from langchain_chroma import Chroma
from langchain.schema import Document
import uuid
from src.JarvisChain.models.llm_models import embedding_model
from src.JarvisChain.config.config import VECTOR_DB_CONFIG

class VectorStore:
    def __init__(self):
        try:
            self.db = Chroma(
                collection_name=VECTOR_DB_CONFIG["collection_name"],
                embedding_function=embedding_model,
                persist_directory=VECTOR_DB_CONFIG["persist_directory"]
            )
        except Exception as e:
            print(f"Creating new vector database: {e}")
            self.db = Chroma.from_documents(
                documents=[],
                embedding=embedding_model,
                collection_name=VECTOR_DB_CONFIG["collection_name"],
                persist_directory=VECTOR_DB_CONFIG["persist_directory"]
            )
    
    def add_document(self, content: str, metadata: dict = None):
        """Add document to vector database"""
        try:
            if metadata is None:
                metadata = {}
            
            document = Document(
                page_content=content,
                metadata={
                    "type": "user_profile",
                    "timestamp": str(uuid.uuid4()),
                    **metadata
                }
            )
            
            self.db.add_documents(
                documents=[document],
                ids=[str(uuid.uuid4())]
            )
            return True
        except Exception as e:
            print(f"Failed to save document: {e}")
            return False
    
    def search(self, query: str, k: int = 5):
        """Search for similar documents"""
        try:
            return self.db.similarity_search(query, k=k)
        except Exception as e:
            print(f"Search failed: {e}")
            return [] 