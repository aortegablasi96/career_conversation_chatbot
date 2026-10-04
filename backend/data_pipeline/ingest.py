try:
    # Local only: trust the OS certificate store (e.g. antivirus HTTPS scanning on Windows).
    # Not in requirements.txt, so this is a no-op on Render.
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import os
import glob
import pickle
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.retrievers import BM25Retriever

from dotenv import load_dotenv

DB_NAME = str(Path(__file__).parent.parent / "storage" / "vector_db")
BM25_PATH = Path(__file__).parent.parent / "storage" / "bm25_index.pkl"
KNOWLEDGE_BASE = str(Path(__file__).parent.parent / "knowledge-base")

load_dotenv(override=True)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


def fetch_documents():
    folders = glob.glob(str(Path(KNOWLEDGE_BASE) / "*"))
    documents = []
    for folder in folders:
        doc_type = os.path.basename(folder)
        loader = DirectoryLoader(
            folder, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"}
        )
        folder_docs = loader.load()
        for doc in folder_docs:
            doc.metadata["doc_type"] = doc_type
            documents.append(doc)
    return documents


def enrich_documents(documents):
    """Prepend a source-context prefix and assign a chunk_id to every document. No splitting."""
    basename_cache: dict[str, str] = {}
    for i, doc in enumerate(documents):
        source = doc.metadata.get("source", "")
        doc_type = doc.metadata.get("doc_type", "")
        if source not in basename_cache:
            stem = Path(source).stem
            basename_cache[source] = stem.replace("_", " ").replace("-", " ")
        clean_name = basename_cache[source]
        doc.page_content = f"[Category: {doc_type} | Document: {clean_name}]\n{doc.page_content}"
        doc.metadata["chunk_id"] = f"{source}::0"
    return documents


def create_embeddings(chunks):
    if os.path.exists(DB_NAME):
        Chroma(persist_directory=DB_NAME, embedding_function=embeddings).delete_collection()

    vectorstore = Chroma.from_documents(
        documents=chunks, embedding=embeddings, persist_directory=DB_NAME
    )

    collection = vectorstore._collection
    count = collection.count()

    sample_embedding = collection.get(limit=1, include=["embeddings"])["embeddings"][0]
    dimensions = len(sample_embedding)
    print(f"There are {count:,} vectors with {dimensions:,} dimensions in the vector store")
    return vectorstore


def save_bm25(chunks):
    bm25 = BM25Retriever.from_documents(chunks)
    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25, f)
    print(f"BM25 index saved to {BM25_PATH}")


if __name__ == "__main__":
    documents = fetch_documents()
    documents = enrich_documents(documents)
    print(f"Prepared {len(documents)} documents (no chunking)")
    vectorstore = create_embeddings(documents)
    save_bm25(documents)
    print("Ingestion complete")
