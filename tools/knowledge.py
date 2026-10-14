import os
import docx
import openpyxl
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Base paths
WORKSPACE_DIR = os.path.abspath(os.path.join(os.getcwd(), "workspace"))
KNOWLEDGE_DIR = os.path.join(WORKSPACE_DIR, "knowledge_base")
DB_DIR = os.path.abspath(os.path.join(os.getcwd(), "chroma_db"))

os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# Initialize local embedding model
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def build_knowledge_base() -> str:
    """
    Indexes all PDF, TXT, DOCX, and XLSX files in 'workspace/knowledge_base' into the vector database.
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Auto-syncing knowledge base from '{KNOWLEDGE_DIR}'...")
    try:
        docs = []
        for root, _, files in os.walk(KNOWLEDGE_DIR):
            for file in files:
                filepath = os.path.join(root, file)
                
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
        
        if not docs:
            return "No documents found in knowledge base."
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_documents(docs)
        
        # Build / overwrite vector store
        Chroma.from_documents(chunks, embeddings, persist_directory=DB_DIR)
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
            
        extracted_info = [
            f"Source: {res.metadata.get('source', 'Unknown')}\nContent:\n{res.page_content}" 
            for res in results
        ]
        return "\n\n---\n\n".join(extracted_info)
        
    except Exception as e:
        return f"Knowledge base search failed: {e}"