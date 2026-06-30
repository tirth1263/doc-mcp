import re
from openai import OpenAI
from src.config import NEBIUS_API_KEY, NEBIUS_BASE_URL, EMBEDDING_MODEL, LLM_MODEL, CHUNK_SIZE

_client = None


def get_client() -> OpenAI:
    """Lazily initialize the Nebius/OpenAI client so the app can start without keys."""
    global _client
    if _client is None:
        if not NEBIUS_API_KEY:
            raise RuntimeError(
                "NEBIUS_API_KEY is not set. Add it as a Space secret / .env variable "
                "to enable embeddings and Q&A."
            )
        _client = OpenAI(api_key=NEBIUS_API_KEY, base_url=NEBIUS_BASE_URL)
    return _client


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """Split markdown text into overlapping chunks."""
    # Split on headers or paragraphs first
    sections = re.split(r"\n(?=#{1,3} )", text)
    chunks = []
    current = ""
    for section in sections:
        if len(current) + len(section) <= chunk_size:
            current += "\n" + section
        else:
            if current.strip():
                chunks.append(current.strip())
            # If section itself is too large, split by paragraphs
            if len(section) > chunk_size:
                paragraphs = section.split("\n\n")
                para_buf = ""
                for para in paragraphs:
                    if len(para_buf) + len(para) <= chunk_size:
                        para_buf += "\n\n" + para
                    else:
                        if para_buf.strip():
                            chunks.append(para_buf.strip())
                        para_buf = para
                if para_buf.strip():
                    chunks.append(para_buf.strip())
                current = ""
            else:
                current = section
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 50]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a list of texts via Nebius."""
    if not texts:
        return []
    batch_size = 32
    all_embeddings = []
    client = get_client()
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings


def generate_answer(question: str, context_chunks: list[dict]) -> str:
    """Generate an answer from context chunks using the LLM."""
    context_text = "\n\n---\n\n".join(
        f"**Source: {c['path']}**\n{c['content']}" for c in context_chunks
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful documentation assistant. Answer questions accurately "
                "based only on the provided documentation context. Include source file "
                "references when citing information. If the answer is not in the context, "
                "say so clearly."
            ),
        },
        {
            "role": "user",
            "content": f"Documentation context:\n\n{context_text}\n\nQuestion: {question}",
        },
    ]
    response = get_client().chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
    )
    return response.choices[0].message.content
