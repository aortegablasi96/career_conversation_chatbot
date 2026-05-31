import os
import glob
import pickle
import shutil
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
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


MIN_CHUNK_CHARS = 300


def create_chunks(documents):
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,
    )
    char_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    all_chunks = []
    for doc in documents:
        doc_type = doc.metadata.get("doc_type", "")
        source = doc.metadata.get("source", "")

        if len(doc.page_content.strip()) < MIN_CHUNK_CHARS:
            all_chunks.append(doc)
        else:
            header_splits = header_splitter.split_text(doc.page_content)
            for split in header_splits:
                split.metadata["doc_type"] = doc_type
                split.metadata["source"] = source
            char_splits = char_splitter.split_documents(header_splits)
            all_chunks.extend(char_splits)

    basename_cache: dict[str, str] = {}
    for i, chunk in enumerate(all_chunks):
        source = chunk.metadata.get("source", "")
        doc_type = chunk.metadata.get("doc_type", "")
        if source not in basename_cache:
            stem = Path(source).stem
            basename_cache[source] = stem.replace("_", " ").replace("-", " ")
        clean_name = basename_cache[source]
        chunk.page_content = f"[Category: {doc_type} | Document: {clean_name}]\n{chunk.page_content}"
        chunk.metadata["chunk_id"] = f"{source}::{i}"

    return all_chunks


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
    chunks = create_chunks(documents)
    print(f"Created {len(chunks)} chunks from {len(documents)} documents")
    vectorstore = create_embeddings(chunks)
    save_bm25(chunks)
    print("Ingestion complete")
