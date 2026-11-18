import os
import docx
import openpyxl
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import sqlite3
from contextlib import closing
from pathlib import Path
from indexing.fingerprints import file_sha256
from indexing.manifest import initialize_manifest
import json

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
    },
    sort_keys=True,
)


# Base paths
WORKSPACE_DIR = os.path.abspath(os.path.join(os.getcwd(), "workspace"))
KNOWLEDGE_DIR = os.path.join(WORKSPACE_DIR, "knowledge_base")
DB_DIR = os.path.abspath(os.path.join(os.getcwd(), "chroma_db"))

os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# Initialize local embedding model
embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)

def build_knowledge_base() -> str:
    index_dir = Path(DB_DIR)
    index_dir.mkdir(parents=True, exist_ok=True)
    return _build_knowledge_base(index_dir / "manifest.sqlite3")


def _build_knowledge_base(manifest_path: Path | None = None) -> str:

    """
    Indexes all PDF, TXT, DOCX, and XLSX files in 'workspace/knowledge_base' into the vector database.
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Auto-syncing knowledge base from '{KNOWLEDGE_DIR}'...")
    try:
        docs = []
        config = INDEX_CONFIG
        known = {}
        pending = []
        skipped = 0

        if manifest_path is not None:
            initialize_manifest(manifest_path)
            with closing(sqlite3.connect(manifest_path)) as db:
                rows = db.execute(
                    "SELECT relative_path, size_bytes, mtime_ns, index_config "
                    "FROM indexed_files"
                )
                known = {path: (size, mtime, cfg) for path, size, mtime, cfg in rows}


        for root, _, files in os.walk(KNOWLEDGE_DIR):
            for file in files:
                filepath = os.path.join(root, file)

                if not file.endswith((".txt", ".pdf", ".docx", ".xlsx")):
                    print(f"[System Warning]: Unsupported file type skipped: {file}")
                    continue

                if manifest_path is not None:
                    relative = Path(filepath).relative_to(KNOWLEDGE_DIR).as_posix()
                    stat = os.stat(filepath)
                    current = (stat.st_size, stat.st_mtime_ns, config)

                    if known.get(relative) == current:
                        skipped += 1
                        continue

                    if relative in known:
                        raise RuntimeError(f"Changed file needs replacement: {relative}")

                    fingerprint = file_sha256(filepath)
                    docs_before = len(docs)
                
                if file.endswith(".txt"):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        docs.append(Document(page_content=f.read(), metadata={"source": file}))
                        
                elif file.endswith(".pdf"):
                    text = ""
                    try:
                        reader = PdfReader(filepath)
                        for page in reader.pages:
                            extracted = page.extract_text()
                            if extracted:
                                text += extracted + "\n"
                        docs.append(Document(page_content=text, metadata={"source": file}))
                    except Exception as e:
                        print(f"[System Warning]: Could not read PDF {file}: {e}")

                elif file.endswith(".docx"):
                    try:
                        doc = docx.Document(filepath)
                        text = "\n".join([para.text for para in doc.paragraphs])
                        docs.append(Document(page_content=text, metadata={"source": file}))
                    except Exception as e:
                        print(f"[System Warning]: Could not read DOCX {file}: {e}")

                elif file.endswith(".xlsx"):
                    try:
                        wb = openpyxl.load_workbook(filepath, data_only=True)
                        text = ""
                        for sheet in wb.worksheets:
                            text += f"--- Sheet: {sheet.title} ---\n"
                            for row in sheet.iter_rows(values_only=True):
                                row_data = " ".join([str(cell) for cell in row if cell is not None])
                                if row_data:
                                    text += row_data + "\n"
                        docs.append(Document(page_content=text, metadata={"source": file}))
                    except Exception as e:
                        print(f"[System Warning]: Could not read XLSX {file}: {e}")


                if manifest_path is not None and len(docs) > docs_before:
                    if docs[-1].page_content.strip():
                        pending.append((relative, stat.st_size, stat.st_mtime_ns, fingerprint, INDEX_CONFIG))

        if not docs:
            if skipped:
                return f"Successfully indexed 0 documents; skipped {skipped} unchanged."
            return "No documents found in knowledge base."
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        chunks = text_splitter.split_documents(docs)
        Chroma.from_documents(chunks, embeddings, persist_directory=DB_DIR)

        if manifest_path is not None and pending:
            with closing(sqlite3.connect(manifest_path)) as db:
                db.executemany(
                    "INSERT INTO indexed_files "
                    "(relative_path, size_bytes, mtime_ns, sha256, index_config) "
                    "VALUES (?, ?, ?, ?, ?)",
                    pending,
                )
                db.commit()

        return f"Successfully indexed {len(docs)} documents ({len(chunks)} chunks)."
    except Exception as e:
        return f"Failed to build knowledge base: {e}"

def search_knowledge_base(query: str, auto_sync: bool = True, k: int = 3) -> str:
    """
    Searches your personal documents (PDFs, notes, docs, spreadsheets) for relevant information.
    Automatically syncs and indexes any new documents before searching.
    
    Args:
        query: The specific topic, question, or term to search for in your documents.
        auto_sync: Whether to automatically refresh the index before searching (default: True).
        k: The number of most relevant results to return (default: 3).
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Accessing knowledge base for '{query}'...")
    try:
        # If DB doesn't exist yet or auto_sync is enabled, index the files first
        if not os.path.exists(DB_DIR) or auto_sync:
            build_knowledge_base()

        db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
        results = db.similarity_search(query, k=k)
        
        if not results:
            return "No relevant information found in the documents."
            
        extracted_info = [f"Source: {res.metadata.get('source', 'Unknown')}\nContent:\n{res.page_content}" for res in results]
        return "\n\n---\n\n".join(extracted_info)
        
    except Exception as e:
        return f"Knowledge base search failed: {e}"