from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from src.config.config import VECTOR_DB_CONFIG, OPENAI_API_KEY
from src.utils.logger import get_logger

# Get logger
logger = get_logger('memory')

class MemoryManager:
    """长期知识存储管理器"""
    def __init__(self):
        self._init_vector_db()
    
    def _init_vector_db(self):
        """初始化向量数据库"""
        try:
            # 初始化嵌入模型
            self.embedding_model = OpenAIEmbeddings(
                model=VECTOR_DB_CONFIG["embedding_model"],
                openai_api_key=OPENAI_API_KEY
            )
            
            # 获取或创建向量数据库
            self.vector_db = Chroma(
                collection_name=VECTOR_DB_CONFIG["collection_name"],
                embedding_function=self.embedding_model,
                persist_directory=VECTOR_DB_CONFIG["persist_directory"]
            )
            logger.info("向量数据库初始化成功")
        except Exception as e:
            logger.error(f"初始化向量数据库时发生错误: {str(e)}")
            raise
    
    async def add_to_memory(self, text: str) -> bool:
        """添加信息到长期记忆"""
        try:
            # 保存到向量数据库
            doc = Document(page_content=text)
            self.vector_db.add_documents([doc])
            self.vector_db.persist()
            
            logger.info("信息已成功保存到长期记忆")
            return True
        except Exception as e:
            logger.error(f"保存到长期记忆时发生错误: {str(e)}")
            return False
    
    async def get_relevant_memories(self, query: str, k: int = 3) -> list:
        """搜索相关的长期记忆"""
        try:
            # 从向量数据库搜索
            results = self.vector_db.similarity_search(query, k=k)
            return results
        except Exception as e:
            logger.error(f"搜索长期记忆时发生错误: {str(e)}")
            return []
    
    async def get_all_memories(self) -> list:
        """获取所有长期记忆"""
        try:
            # 从向量数据库获取所有文档
            results = self.vector_db.get()
            if results and 'documents' in results:
                return [doc.page_content for doc in results['documents']]
            return []
        except Exception as e:
            logger.error(f"获取所有长期记忆时发生错误: {str(e)}")
            return [] 