from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    database_hostname:str
    database_port:str
    database_password:str
    database_name:str
    database_username:str
    secret_key:str
    algorithm:str
    access_token_expire_minutes:int
    groq_api_key: str
    gemini_api_key: str                        # ← add this
    groq_model: str = "llama-3.1-8b-instant"
    embed_dim: int = 3072                       # ← 768 → 3072
    chunk_size: int = 512
    chunk_overlap: int = 64
    rag_top_k: int = 5
    conversation_history_limit: int = 20
    
    model_config=SettingsConfigDict(env_file=".env")

settings = Settings()