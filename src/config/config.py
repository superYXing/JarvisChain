import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API key configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model configuration
MODEL_CONFIG = {
    "user_profile": {
        "model_name": "gpt-3.5-turbo",
        "temperature": 0
    },
    "intent": {
        "model_name": "gpt-3.5-turbo",
        "temperature": 0
    },
    "analysis": {
        "model_name": "gpt-3.5-turbo",
        "temperature": 0.2
    },
    "summary": {
        "model_name": "gpt-3.5-turbo",
        "temperature": 0.2
    },
    "decision": {
        "model_name": "gpt-3.5-turbo",
        "temperature": 0
    }
}

# Vector database configuration
VECTOR_DB_CONFIG = {
    "collection_name": "user_profiles",
    "embedding_model": "text-embedding-ada-002",
    "persist_directory": "./chroma_db"
}

# Short-term memory configuration
MEMORY_CONFIG = {
    "max_history": 10
} 