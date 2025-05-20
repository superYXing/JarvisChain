from langchain.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from src.config.config import VECTOR_DB_CONFIG, OPENAI_API_KEY
from src.utils.logger import get_logger

# Get logger
logger = get_logger('user_profile')

class UserProfileManager:
    """User profile manager"""
    def __init__(self):
        self.user_profiles = []  # List of user profiles in memory
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
    
    async def is_user_profile_info(self, text: str) -> bool:
        """Check if text contains user profile information"""
        # More complex logic can be added here
        profile_keywords = ["name", "age", "gender", "occupation", "interests", "hobbies"]
        return any(keyword in text.lower() for keyword in profile_keywords)
    
    async def save_user_profile(self, profile_info: str) -> bool:
        """Save user profile information"""
        try:
            # Save to memory
            self.user_profiles.append(profile_info)
            
            # Save to vector database
            doc = Document(page_content=profile_info)
            self.vector_db.add_documents([doc])
            self.vector_db.persist()
            
            logger.info("User profile information saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving user profile information: {str(e)}")
            return False
    
    async def search_user_profiles(self, query: str, k: int = 3) -> list:
        """Search user profile information"""
        try:
            # Search from vector database
            results = self.vector_db.similarity_search(query, k=k)
            return [doc.page_content for doc in results]
        except Exception as e:
            logger.error(f"Error searching user profile information: {str(e)}")
            return []
    
    async def get_all_profiles(self) -> list:
        """Get all user profile information"""
        try:
            # Get all documents from vector database
            results = self.vector_db.get()
            if results and 'documents' in results:
                return [doc.page_content for doc in results['documents']]
            return []
        except Exception as e:
            logger.error(f"Error getting all user profile information: {str(e)}")
            return []
    
    async def search_relevant_memory(self, query: str, k: int = 3) -> str:
        """Search relevant memories"""
        try:
            results = self.vector_db.similarity_search(query, k=k)
            if results:
                memory_context = "\n".join([doc.page_content for doc in results])
                return f"Relevant historical information:\n{memory_context}\n\nCurrent user input: {query}"
            return query
        except Exception as e:
            logger.error(f"Error searching memories: {str(e)}")
            return query 