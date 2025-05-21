from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from src.config.config import VECTOR_DB_CONFIG, OPENAI_API_KEY
from src.utils.logger import get_logger
from langchain.schema import SystemMessage, HumanMessage
from langchain.llms import OpenAI
from src.models.llm_models import DECISION_MODEL

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
        """使用大模型判断文本是否包含用户信息"""
        try:
            system_prompt = """你是一个用户信息分析专家。你的任务是判断给定的文本是否包含用户个人信息。
请仔细分析文本，判断是否包含以下类型的信息：
1. 基本信息：姓名、年龄、性别、职业等
2. 个人特征：身高、体重、外貌特征等
3. 联系方式：电话、邮箱、地址等
4. 个人偏好：兴趣爱好、生活习惯、饮食偏好等
5. 其他个人信息

请只返回 "true" 或 "false"，不要包含其他任何文字。
- 如果文本包含任何上述类型的个人信息，返回 "true"
- 如果文本不包含任何个人信息，返回 "false"
- 如果文本只是普通的问候或对话，返回 "false"
- 如果文本包含个人信息但同时也包含其他内容，返回 "true"

示例：
输入："我叫张三，今年25岁"
输出："true"

输入："你好，今天天气真好"
输出："false"

输入："我喜欢看电影，特别是科幻片"
输出："true"
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=text)
            ]
            
            result = DECISION_MODEL.invoke(messages)
            # 确保返回的是布尔值
            return result.content.strip().lower() == "true"
            
        except Exception as e:
            logger.error(f"判断用户信息时发生错误: {str(e)}")
            # 发生错误时返回False，避免误判
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