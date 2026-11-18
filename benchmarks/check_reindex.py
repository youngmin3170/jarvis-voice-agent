from pathlib import Path
import importlib.util
import tempfile
from time import perf_counter
from statistics import median
import shutil

class TimedEmbeddings:
    def __init__(self, inner):
        self.inner = inner
        self.document_ms = 0.0

    def embed_documents(self, texts):
        start = perf_counter()
        try:
            return self.inner.embed_documents(texts)
        finally:
            self.document_ms += (perf_counter() - start) * 1000

    def embed_query(self, text):
        return self.inner.embed_query(text)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load only knowledge.py, avoiding unrelated imports in tools/__init__.py.
spec = importlib.util.spec_from_file_location("knowledge_under_test", PROJECT_ROOT / "tools" / "knowledge.py")
knowledge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(knowledge)

timed_embeddings = TimedEmbeddings(knowledge.embeddings)
knowledge.embeddings = timed_embeddings

# Redirect indexing to a separate test workspace.
test_root = Path(tempfile.mkdtemp(prefix="jarvis-reindex-"))
test_docs = test_root / "documents"
test_docs.mkdir()

knowledge.KNOWLEDGE_DIR = str(test_docs)
knowledge.DB_DIR = str(test_root / "chroma_db")

shutil.copytree(PROJECT_ROOT / "workspace" / "knowledge_base", test_docs, dirs_exist_ok=True)
print(f"Test workspace: {test_root}")

index_times = []

for attempt in range(1, 7):
    timed_embeddings.document_ms = 0.0
    start = perf_counter()
    result = knowledge._build_knowledge_base(test_root / "manifest.sqlite3")
    elapsed_ms = (perf_counter() - start) * 1000
    index_times.append(elapsed_ms)
    
    print(f"\nIndexing attempt {attempt}: {result}")

    embedding_ms = timed_embeddings.document_ms
    other_ms = elapsed_ms - embedding_ms
    
    print(f"  Document embedding: {embedding_ms:.2f} ms")
    print(f"  Other indexing work: {other_ms:.2f} ms")
    print(f"Indexing time: {elapsed_ms:.2f} ms")

    if not result.startswith("Successfully indexed"):
        raise SystemExit("Indexing failed; stop here and inspect the error.")

    db = knowledge.Chroma(
        persist_directory=knowledge.DB_DIR,
        embedding_function=knowledge.embeddings,
    )
    records = db.get(include=["documents"])
    print(f"Stored records: {len(records['ids'])}")
    # print(f"Stored texts: {records['documents']}")


print(f"\nFirst indexing call: {index_times[0]:.2f} ms")
print(f"Subsequent calls: {[round(ms, 2) for ms in index_times[1:]]}")
print(f"Median of subsequent calls: {median(index_times[1:]):.2f} ms")