from datetime import datetime, timezone
from pymongo import MongoClient, UpdateOne
from pymongo.operations import SearchIndexModel
from src.config import (
    MONGODB_URI, DB_NAME, COLLECTION_RAG, COLLECTION_REPOS,
    VECTOR_INDEX_NAME, EMBEDDING_DIM, SIMILARITY_TOP_K,
)


def get_db():
    client = MongoClient(MONGODB_URI)
    return client[DB_NAME]


def ensure_vector_index(db):
    """Create vector search index if it doesn't exist."""
    collection = db[COLLECTION_RAG]
    try:
        existing = list(collection.list_search_indexes())
        if any(idx["name"] == VECTOR_INDEX_NAME for idx in existing):
            return
        index_model = SearchIndexModel(
            definition={
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": EMBEDDING_DIM,
                        "similarity": "cosine",
                    },
                    {"type": "filter", "path": "repo"},
                ]
            },
            name=VECTOR_INDEX_NAME,
            type="vectorSearch",
        )
        collection.create_search_index(index_model)
        print(f"Vector search index '{VECTOR_INDEX_NAME}' creation initiated.")
    except Exception as e:
        print(f"Index setup note: {e}")


def upsert_chunks(db, repo: str, file_path: str, chunks: list[str], embeddings: list[list[float]], sha: str, file_url: str):
    collection = db[COLLECTION_RAG]
    ops = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        doc_id = f"{repo}::{file_path}::{i}"
        ops.append(
            UpdateOne(
                {"_id": doc_id},
                {"$set": {
                    "_id": doc_id,
                    "repo": repo,
                    "path": file_path,
                    "chunk_index": i,
                    "content": chunk,
                    "embedding": emb,
                    "sha": sha,
                    "url": file_url,
                    "updated_at": datetime.now(timezone.utc),
                }},
                upsert=True,
            )
        )
    if ops:
        collection.bulk_write(ops)


def delete_file_chunks(db, repo: str, file_path: str):
    db[COLLECTION_RAG].delete_many({"repo": repo, "path": file_path})


def delete_repo(db, repo: str):
    db[COLLECTION_RAG].delete_many({"repo": repo})
    db[COLLECTION_REPOS].delete_one({"repo": repo})


def get_file_shas(db, repo: str) -> dict[str, str]:
    """Return {path: sha} for all files already ingested for this repo."""
    docs = db[COLLECTION_RAG].find({"repo": repo}, {"path": 1, "sha": 1, "chunk_index": 1})
    result = {}
    for doc in docs:
        if doc.get("chunk_index", 0) == 0:
            result[doc["path"]] = doc["sha"]
    return result


def upsert_repo_meta(db, repo: str, owner: str, file_count: int):
    db[COLLECTION_REPOS].update_one(
        {"repo": repo},
        {"$set": {
            "repo": repo,
            "owner": owner,
            "file_count": file_count,
            "last_ingested": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


def list_repos(db) -> list[dict]:
    return list(db[COLLECTION_REPOS].find({}, {"_id": 0}))


def vector_search(db, repo: str, query_embedding: list[float], top_k: int = SIMILARITY_TOP_K) -> list[dict]:
    collection = db[COLLECTION_RAG]
    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": top_k * 10,
                "limit": top_k,
                "filter": {"repo": {"$eq": repo}},
            }
        },
        {"$project": {"_id": 0, "content": 1, "path": 1, "url": 1, "score": {"$meta": "vectorSearchScore"}}},
    ]
    return list(collection.aggregate(pipeline))


def get_repo_stats(db, repo: str) -> dict:
    total_chunks = db[COLLECTION_RAG].count_documents({"repo": repo})
    file_count = len(db[COLLECTION_RAG].distinct("path", {"repo": repo}))
    meta = db[COLLECTION_REPOS].find_one({"repo": repo}, {"_id": 0})
    return {
        "total_chunks": total_chunks,
        "file_count": file_count,
        "last_ingested": meta.get("last_ingested") if meta else None,
    }
