#!/usr/bin/env python3
"""Database setup and status utility."""
import sys
from pymongo import MongoClient
from pymongo.operations import SearchIndexModel

sys.path.insert(0, ".")
from src.config import MONGODB_URI, DB_NAME, COLLECTION_RAG, COLLECTION_REPOS, VECTOR_INDEX_NAME, EMBEDDING_DIM


def setup():
    print(f"Connecting to MongoDB...")
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]

    # Create collections
    existing = db.list_collection_names()
    for col in [COLLECTION_RAG, COLLECTION_REPOS]:
        if col not in existing:
            db.create_collection(col)
            print(f"Created collection: {col}")
        else:
            print(f"Collection already exists: {col}")

    # Create basic indexes
    db[COLLECTION_RAG].create_index([("repo", 1), ("path", 1)])
    db[COLLECTION_RAG].create_index([("repo", 1), ("chunk_index", 1)])
    db[COLLECTION_REPOS].create_index([("repo", 1)], unique=True)
    print("Basic indexes created.")

    # Vector search index
    collection = db[COLLECTION_RAG]
    try:
        existing_indexes = list(collection.list_search_indexes())
        if any(idx["name"] == VECTOR_INDEX_NAME for idx in existing_indexes):
            print(f"Vector search index '{VECTOR_INDEX_NAME}' already exists.")
        else:
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
            print(f"Vector search index '{VECTOR_INDEX_NAME}' creation initiated (may take a few minutes).")
    except Exception as e:
        print(f"Vector index note: {e}")

    print("\nSetup complete!")
    client.close()


def status():
    print(f"Connecting to MongoDB...")
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]

    rag_count = db[COLLECTION_RAG].count_documents({})
    repo_count = db[COLLECTION_REPOS].count_documents({})
    repos = list(db[COLLECTION_REPOS].find({}, {"repo": 1, "file_count": 1, "last_ingested": 1, "_id": 0}))

    print(f"\nDatabase: {DB_NAME}")
    print(f"Total chunks: {rag_count}")
    print(f"Total repos: {repo_count}")
    if repos:
        print("\nIngested repositories:")
        for r in repos:
            print(f"  - {r['repo']} ({r.get('file_count', '?')} files, last: {r.get('last_ingested', 'unknown')})")

    try:
        indexes = list(db[COLLECTION_RAG].list_search_indexes())
        print(f"\nSearch indexes: {[idx['name'] for idx in indexes]}")
    except Exception as e:
        print(f"\nSearch index check: {e}")

    client.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if cmd == "setup":
        setup()
    elif cmd == "status":
        status()
    else:
        print(f"Unknown command: {cmd}. Use 'setup' or 'status'.")
