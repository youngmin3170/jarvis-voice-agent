import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
import docx
import openpyxl
from filelock import FileLock
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from indexing.fingerprints import file_sha256
from indexing.manifest import initialize_manifest


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
PARSER_VERSION = 1
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

INDEX_CONFIG = json.dumps(
    {
        "model": MODEL_NAME,
        "parser_version": PARSER_VERSION,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "chunk_id_version": 1,
    },
    sort_keys=True,
)

WORKSPACE_DIR = Path.cwd() / "workspace"
KNOWLEDGE_DIR = WORKSPACE_DIR / "knowledge_base"
DB_DIR = Path.cwd() / "chroma_db"

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx", ".xlsx"}

KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)


def _read_text(path: Path) -> str:
    """Extract the text of one supported document."""
    extension = path.suffix.lower()

    if extension == ".txt":
        return path.read_text(encoding="utf-8")

    if extension == ".pdf":
        with path.open("rb") as stream:
            reader = PdfReader(stream)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n".join(pages)

    if extension == ".docx":
        document = docx.Document(path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    if extension == ".xlsx":
        lines = []
        with closing(openpyxl.load_workbook(path, read_only=True, data_only=True)) as workbook:
            for sheet in workbook.worksheets:
                lines.append(f"--- Sheet: {sheet.title} ---")

                for row in sheet.values:
                    text = " ".join(str(value) for value in row if value is not None)
                    if text:
                        lines.append(text)

        return "\n".join(lines)

    raise ValueError(f"Unsupported file type: {extension}")

def _open_store():
    return Chroma(persist_directory=str(DB_DIR), embedding_function=embeddings)


def _replace_chunks(store, relative_path: str, chunks) -> None:
    """Replace this file's chunks and remove any that no longer exist."""
    old_ids = store.get(where={"source": relative_path}, include=[])["ids"]

    # Reuse IDs on every edit: notes.txt:0, notes.txt:1, ...
    new_ids = [f"{relative_path}:{number}" for number in range(len(chunks))]

    if chunks:
        store.add_documents(chunks, ids=new_ids)

    # Example: the old file had 5 chunks, but the new file has only 3.
    # IDs 0, 1, 2 were updated above. Delete IDs 3 and 4.
    obsolete_ids = set(old_ids) - set(new_ids)
    if obsolete_ids:
        store.delete(ids=list(obsolete_ids))


def _raise_scan_error(error):
    # A folder that could not be read should not be treated as deleted.
    raise error


def _sync(manifest_path: Path) -> str:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    chroma_file = Path(DB_DIR) / "chroma.sqlite3"

    if chroma_file.exists() and not manifest_path.exists():
        raise RuntimeError("Existing Chroma index has no matching manifest.")

    initialize_manifest(manifest_path)

    root = Path(KNOWLEDGE_DIR)
    files = {}

    for folder, _, filenames in os.walk(root, onerror=_raise_scan_error):
        for filename in filenames:
            path = Path(folder) / filename
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                relative_path = path.relative_to(root).as_posix()
                files[relative_path] = path

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    indexed = 0
    chunk_count = 0
    skipped = 0
    deleted = 0
    failures = []

    with closing(sqlite3.connect(manifest_path)) as db:
        # A row here means a previous update began but did not finish.
        db.execute(
            "CREATE TABLE IF NOT EXISTS dirty_files "
            "(relative_path TEXT PRIMARY KEY)"
        )
        db.commit()

        rows = db.execute(
            "SELECT relative_path, size_bytes, mtime_ns, sha256, index_config "
            "FROM indexed_files"
        )
        known = {}
        for relative_path, size, mtime, saved_hash, config in rows:
            known[relative_path] = (size, mtime, saved_hash, config)

        if known and not chroma_file.exists():
            raise RuntimeError("Manifest exists, but its Chroma index is missing.")

        dirty = {row[0] for row in db.execute("SELECT relative_path FROM dirty_files")}

        store = _open_store()

        # Include remembered paths so we can also detect deleted files.
        all_paths = set(files) | set(known) | dirty

        for relative_path in sorted(all_paths):
            try:
                path = files.get(relative_path)
                previous = known.get(relative_path)

                if path is not None:
                    stat = path.stat()
                    size = stat.st_size
                    mtime = stat.st_mtime_ns

                    can_reuse = (previous is not None and relative_path not in dirty and previous[3] == INDEX_CONFIG)

                    # Same size, timestamp, and config: skip without hashing.
                    if can_reuse and previous[:2] == (size, mtime):
                        skipped += 1
                        continue

                    current_hash = file_sha256(path)

                    # Metadata changed, but the contents are identical.
                    if can_reuse and previous[2] == current_hash:
                        with db:
                            db.execute(
                                "UPDATE indexed_files "
                                "SET size_bytes = ?, mtime_ns = ? "
                                "WHERE relative_path = ?",
                                (size, mtime, relative_path),
                            )
                        skipped += 1
                        continue

                # New, changed, deleted, or interrupted. Remember that work is in progress before writing anything to Chroma.
                with db:
                    db.execute(
                        "INSERT OR IGNORE INTO dirty_files (relative_path) "
                        "VALUES (?)",
                        (relative_path,),
                    )

                chunks = []
                if path is not None:
                    text = _read_text(path)
                    document = Document(page_content=text, metadata={"source": relative_path})
                    chunks = splitter.split_documents([document])

                    if file_sha256(path) != current_hash:
                        raise RuntimeError("File changed while it was being read.")

                # For a deleted or empty file, an empty list removes its old chunks.
                _replace_chunks(store, relative_path, chunks)

                # Record success only after the Chroma operation succeeds.
                with db:
                    if path is None:
                        db.execute(
                            "DELETE FROM indexed_files WHERE relative_path = ?",
                            (relative_path,),
                        )
                        deleted += 1
                    else:
                        db.execute(
                            "INSERT OR REPLACE INTO indexed_files "
                            "(relative_path, size_bytes, mtime_ns, sha256, index_config) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (relative_path, size, mtime, current_hash, INDEX_CONFIG),
                        )
                        indexed += 1
                        chunk_count += len(chunks)

                    db.execute(
                        "DELETE FROM dirty_files WHERE relative_path = ?",
                        (relative_path,),
                    )

            except Exception as error:
                with db:
                    db.execute(
                        "INSERT OR IGNORE INTO dirty_files (relative_path) "
                        "VALUES (?)",
                        (relative_path,),
                    )
                failures.append(f"{relative_path}: {error}")

    if failures:
        raise RuntimeError("Sync incomplete: " + "; ".join(failures))

    return (
        f"Successfully indexed {indexed} documents ({chunk_count} chunks); "
        f"skipped {skipped} unchanged; deleted {deleted}."
    )


def _index_lock():
    index_dir = Path(DB_DIR)
    index_dir.mkdir(parents=True, exist_ok=True)
    return FileLock(str(index_dir / "sync.lock"), timeout=60)


def build_knowledge_base() -> str:
    """Sync personal documents into the searchable knowledge base."""
    return _build_knowledge_base()


def _build_knowledge_base(manifest_path: Path | None = None) -> str:
    if manifest_path is None:
        manifest_path = Path(DB_DIR) / "manifest.sqlite3"

    try:
        with _index_lock():
            return _sync(manifest_path)
    except Exception as error:
        return f"Failed to build knowledge base: {error}"


def search_knowledge_base(query: str, auto_sync: bool = True, k: int = 3) -> str:
    """Search personal documents and return relevant passages with their sources."""
    try:
        with _index_lock():
            index_dir = Path(DB_DIR)
            manifest_path = index_dir / "manifest.sqlite3"

            if auto_sync or not manifest_path.exists() or not (index_dir / "chroma.sqlite3").exists():
                _sync(manifest_path)
            else:
                with closing(sqlite3.connect(manifest_path)) as db:
                    unfinished = db.execute(
                        "SELECT 1 FROM dirty_files LIMIT 1"
                    ).fetchone()
                    if unfinished:
                        raise RuntimeError("An index update is incomplete. Run sync again.")

            results = _open_store().similarity_search(query, k=k)

        if not results:
            return "No relevant information found in the documents."

        return "\n\n---\n\n".join(
            f"Source: {result.metadata['source']}\nContent:\n{result.page_content}"
            for result in results
        )

    except Exception as error:
        return f"Knowledge base search failed: {error}"