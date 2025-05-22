from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from src.JarvisChain.config.config import VECTOR_DB_CONFIG, OPENAI_API_KEY
from src.JarvisChain.utils.logger import get_logger
from langchain.schema import SystemMessage, HumanMessage
from langchain.llms import OpenAI
from src.JarvisChain.models.llm_models import DECISION_MODEL

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
        """Use large model to determine if text contains user information"""
        try:
            system_prompt = """You are a user information analysis expert. Your task is to determine if the given text contains user personal information.
Please carefully analyze the text to determine if it contains the following types of information:
1. Basic information: name, age, gender, occupation, etc.
2. Personal characteristics: height, weight, appearance, etc.
3. Contact information: phone, email, address, etc.
4. Personal preferences: hobbies, habits, dietary preferences, etc.
5. Other personal information

Please only return "true" or "false", do not include any other text.
- If the text contains any of the above types of personal information, return "true"
- If the text does not contain any personal information, return "false"
- If the text is just a general greeting or conversation, return "false"
- If the text contains personal information but also other content, return "true"

Example:
Input: "My name is Zhang San, I am 25 years old"
Output: "true"

Input: "Hello, the weather is nice today"
Output: "false"

Input: "I like watching movies, especially sci-fi"
Output: "true"
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=text)
            ]
            
            result = DECISION_MODEL.invoke(messages)
            # Ensure the return is a boolean
            return result.content.strip().lower() == "true"
            
        except Exception as e:
            logger.error(f"Error determining user information: {str(e)}")
            # Return False on error to avoid misjudgment
            return False
    
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