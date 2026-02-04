import asyncio
from app.rag import rag_service
import os

DATA_DIR = "/home/tlk/Documents/Projects/my_AItools/bussins_advice/data"

def main():
    print(f"Starting ingestion from {DATA_DIR}...")
    if not os.path.exists(DATA_DIR):
        print(f"Error: Directory {DATA_DIR} not found.")
        return

    rag_service.ingest_documents(DATA_DIR)
    print("Ingestion complete. Vector DB is ready.")

if __name__ == "__main__":
    # Ensure this runs in a way that respects dependencies (sync/async mismatch handling if needed, 
    # but here rag_service methods are sync for simplicity in this script context)
    main()
