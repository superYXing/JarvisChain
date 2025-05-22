from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from src.JarvisChain.config.config import VECTOR_DB_CONFIG, OPENAI_API_KEY
from src.JarvisChain.utils.logger import get_logger

# Get logger
logger = get_logger('memory')

class MemoryManager:
    """Long-term knowledge storage manager"""
    def __init__(self):
        self._init_vector_db()
    
    def _init_vector_db(self):
        """Initialize vector database"""
        try:
            # Initialize embedding model
            self.embedding_model = OpenAIEmbeddings(
                model=VECTOR_DB_CONFIG["embedding_model"],
                openai_api_key=OPENAI_API_KEY
            )
            
            # Get or create vector database
            self.vector_db = Chroma(
                collection_name=VECTOR_DB_CONFIG["collection_name"],
                embedding_function=self.embedding_model,
                persist_directory=VECTOR_DB_CONFIG["persist_directory"]
            )
            logger.info("Vector database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing vector database: {str(e)}")
            raise
    
    async def add_to_memory(self, text: str) -> bool:
        """Add information to long-term memory"""
        try:
            # Save to vector database
            doc = Document(page_content=text)
            self.vector_db.add_documents([doc])
            self.vector_db.persist()
            
            logger.info("Information successfully saved to long-term memory")
            return True
        except Exception as e:
            logger.error(f"Error saving to long-term memory: {str(e)}")
            return False
    
    async def get_relevant_memories(self, query: str, k: int = 3) -> list:
        """Search relevant long-term memories"""
        try:
            # Search from vector database
            results = self.vector_db.similarity_search(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Error searching long-term memories: {str(e)}")
            return []
    
    async def get_all_memories(self) -> list:
        """Get all long-term memories"""
        try:
            # Get all documents from vector database
            results = self.vector_db.get()
            if results and 'documents' in results:
                return [doc.page_content for doc in results['documents']]
            return []
        except Exception as e:
            logger.error(f"Error getting all long-term memories: {str(e)}")
            return [] 