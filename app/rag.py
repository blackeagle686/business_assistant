import os
import logging
from typing import List
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from itertools import islice

MAX_BATCH = 500
def batched(iterable, n):
    """Yield successive n-sized chunks from iterable."""
    """
        description:
            A generator function that takes an iterable and yields successive
            n-sized chunks (batches) from it. Useful for processing large datasets
            in smaller, manageable pieces.
            
        example usage:
        iterable = [1,2,3,4,5,6,7,8]
        n = 3

        # الناتج:
        batch 1 = [1,2,3]
        batch 2 = [4,5,6]
        batch 3 = [7,8]
        batch 4 = [] → الحلقة تتوقف

    """
    
    iterable = iter(iterable)
    while batch := list(islice(iterable, n)):
        yield batch

logger = logging.getLogger(__name__)

# singleton instance of RAGService for use across the app
IS_EMBEDDINGS_LOADED = False
class EmbbedingLoader:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.embedding_function = HuggingFaceEmbeddings(model_name=model_name)

    def load_embeddings(self, documents: List[str]):
        """Convert documents to embeddings."""
        global IS_EMBEDDINGS_LOADED
        if IS_EMBEDDINGS_LOADED:
            logger.info("Embeddings already loaded, skipping.")
            return
        IS_EMBEDDINGS_LOADED = True
        return self.embedding_function.embed_documents(documents)

class RAGService:
    def __init__(self, persist_directory: str = "chroma_db"):
        """
            discription:
                RAGService is responsible for managing the retrieval-augmented generation
                process. It handles document ingestion, embedding, and searching within
                a vector store.
        """
        self.persist_directory = persist_directory
        self.embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embedding_function
        )

    def ingest_documents(self, directory_path: str):
        """Read PDFs from directory and add to vector store."""
        """
            description:
                This method ingests PDF documents from the specified directory,
                processes them into smaller text chunks, converts those chunks into
                embeddings, and stores them in a vector database for later retrieval.

        """
        
        # Check if directory exists 
        """
            description:
                Before attempting to read files, the method verifies that the specified
                directory exists. If it does not, a warning is logged and the method exits early.
        """
        if not os.path.exists(directory_path):
            logger.warning(f"Data directory {directory_path} does not exist.")
            return

        documents = []
        files = [f for f in os.listdir(directory_path) if f.endswith(".pdf")]
        
        for f in files:
            print('-----------------------------------')
            print(f"Found file: {f}")
            
        logger.info(f"Found {len(files)} PDFs to ingest.")
        
        
        # Load and process each PDF
        for file in files:
            file_path = os.path.join(directory_path, file)
            try:
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                documents.extend(docs)
                logger.info(f"Loaded {file}")
            except Exception as e:
                logger.error(f"Error loading {file}: {e}")

        # Split documents into chunks and add to vector store
        if documents:
            # split documents
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(documents)
            
            # Ingest in batches to avoid memory issues 
            """
                description:
                    To efficiently handle large volumes of document chunks without overwhelming
                    memory, the method processes and adds them to the vector store in batches.
            """
            for batch in batched(splits, MAX_BATCH):
                try:
                    self.vector_store.add_documents(batch)
                    self.vector_store.persist()
                    logger.info(f"Ingested {len(splits)} chunks from {len(files)} files.")
                except Exception as e:
                    print(f"Failed batch: {e}")
            
        else:
            logger.info("No documents found/loaded.")

    def search(self, query: str, k: int = 3) -> str:
        """Retrieve relevant context string."""
        results = self.vector_store.similarity_search(query, k=k)
        context = "\n\n".join([f"Source: {doc.metadata.get('source', 'unknown')}\nContent: {doc.page_content}" for doc in results])
        return context

rag_service = RAGService(persist_directory="/content/business_assistant/chroma_db")
