import os
from dotenv import load_dotenv

load_dotenv()

NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
MONGODB_URI = os.getenv("MONGODB_URI", "")
GITHUB_API_KEY = os.getenv("GITHUB_API_KEY", "")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "3072"))
SIMILARITY_TOP_K = int(os.getenv("SIMILARITY_TOP_K", "5"))
GITHUB_CONCURRENT_REQUESTS = int(os.getenv("GITHUB_CONCURRENT_REQUESTS", "10"))

DB_NAME = "doc_mcp"
COLLECTION_RAG = "doc_rag"
COLLECTION_REPOS = "ingested_repos"
VECTOR_INDEX_NAME = "vector_index"
EMBEDDING_MODEL = "BAAI/bge-en-icl"
LLM_MODEL = "meta-llama/Meta-Llama-3.1-70B-Instruct"
EMBEDDING_DIM = 4096
NEBIUS_BASE_URL = "https://api.studio.nebius.com/v1/"
