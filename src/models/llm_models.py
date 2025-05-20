from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from src.config.config import MODEL_CONFIG, OPENAI_API_KEY, VECTOR_DB_CONFIG


# Initialize all LLM models
USER_PROFILE_MODEL = ChatOpenAI(
    model_name=MODEL_CONFIG["user_profile"]["model_name"],
    temperature=MODEL_CONFIG["user_profile"]["temperature"]
)

INTENT_MODEL = ChatOpenAI(
    model_name=MODEL_CONFIG["intent"]["model_name"],
    temperature=MODEL_CONFIG["intent"]["temperature"]
)

ANALYSIS_MODEL = ChatOpenAI(
    model_name=MODEL_CONFIG["analysis"]["model_name"],
    temperature=MODEL_CONFIG["analysis"]["temperature"]
)

SUMMARY_MODEL = ChatOpenAI(
    model_name=MODEL_CONFIG["summary"]["model_name"],
    temperature=MODEL_CONFIG["summary"]["temperature"]
)

# Add decision model
DECISION_MODEL = ChatOpenAI(
    model_name=MODEL_CONFIG["decision"]["model_name"],
    temperature=MODEL_CONFIG["decision"]["temperature"]
)

# Initialize embedding model
embedding_model = OpenAIEmbeddings(
    model=VECTOR_DB_CONFIG["embedding_model"],
    openai_api_key=OPENAI_API_KEY
) 