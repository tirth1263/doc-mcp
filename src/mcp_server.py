"""MCP-compatible tool definitions exposed via Gradio's MCP integration."""
from src.vector_store import get_db, vector_search, list_repos
from src.embeddings import embed_texts, generate_answer


def search_documentation(repo: str, query: str, top_k: int = 5) -> dict:
    """
    Search documentation using semantic similarity.

    Args:
        repo: Repository identifier in format 'owner/repo'
        query: Natural language search query
        top_k: Number of results to return (default 5)

    Returns:
        Dictionary with 'results' list containing matching chunks with paths and scores
    """
    db = get_db()
    embeddings = embed_texts([query])
    if not embeddings:
        return {"error": "Failed to generate query embedding", "results": []}
    results = vector_search(db, repo, embeddings[0], top_k)
    return {"results": results, "query": query, "repo": repo}


def ask_documentation(repo: str, question: str) -> dict:
    """
    Ask a natural language question about documentation and get an AI answer.

    Args:
        repo: Repository identifier in format 'owner/repo'
        question: The question to answer from the documentation

    Returns:
        Dictionary with 'answer' string and 'sources' list of source files used
    """
    db = get_db()
    embeddings = embed_texts([question])
    if not embeddings:
        return {"error": "Failed to generate query embedding", "answer": "", "sources": []}
    results = vector_search(db, repo, embeddings[0])
    if not results:
        return {"answer": "No relevant documentation found for your question.", "sources": []}
    answer = generate_answer(question, results)
    sources = list({r["path"] for r in results})
    return {"answer": answer, "sources": sources, "repo": repo}


def list_available_repos() -> dict:
    """
    List all repositories that have been ingested into the system.

    Returns:
        Dictionary with 'repos' list containing repo names and metadata
    """
    db = get_db()
    repos = list_repos(db)
    return {"repos": repos, "count": len(repos)}
