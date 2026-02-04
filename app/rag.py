import os
import logging
from typing import List
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, persist_directory: str = "chroma_db"):
        self.persist_directory = persist_directory
        self.embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embedding_function
        )

    def ingest_documents(self, directory_path: str):
        """Read PDFs from directory and add to vector store."""
        if not os.path.exists(directory_path):
            logger.warning(f"Data directory {directory_path} does not exist.")
            return

        documents = []
        files = [f for f in os.listdir(directory_path) if f.endswith(".pdf")]
        
        logger.info(f"Found {len(files)} PDFs to ingest.")
        
        for file in files:
            file_path = os.path.join(directory_path, file)
            try:
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                documents.extend(docs)
                logger.info(f"Loaded {file}")
            except Exception as e:
                logger.error(f"Error loading {file}: {e}")

        if documents:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(documents)
            
            # Batch add to avoid limits if necessary, though Chroma handles it well
            self.vector_store.add_documents(documents=splits)
            self.vector_store.persist()
            logger.info(f"Ingested {len(splits)} chunks from {len(files)} files.")
        else:
            logger.info("No documents found/loaded.")

    def search(self, query: str, k: int = 3) -> str:
        """Retrieve relevant context string."""
        results = self.vector_store.similarity_search(query, k=k)
        context = "\n\n".join([f"Source: {doc.metadata.get('source', 'unknown')}\nContent: {doc.page_content}" for doc in results])
        return context

rag_service = RAGService(persist_directory="/home/tlk/Documents/Projects/my_AItools/bussins_advice/chroma_db")
