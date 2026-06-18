"""
Vector store layer — ChromaDB-backed RAG for race control messages.
"""

import os
from typing import Any

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
CHROMA_DIR = os.path.join(DATA_DIR, "chromadb")


def get_chroma_client():
    import chromadb

    return chromadb.PersistentClient(path=CHROMA_DIR)


def get_embedding_fn():
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed_fn(texts: list[str]) -> list[list[float]]:
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    return embed_fn


_COLLECTION_CACHE: dict[str, Any] = {}
_EMBEDDING_FN_CACHE = None


def get_race_control_collection():
    global _COLLECTION_CACHE
    if "race_control" not in _COLLECTION_CACHE:
        client = get_chroma_client()
        _COLLECTION_CACHE["race_control"] = client.get_or_create_collection(
            name="race_control",
            metadata={"hnsw:space": "cosine"},
        )
    return _COLLECTION_CACHE["race_control"]


def index_race_control_messages(session_key: int | str, df_rc) -> None:
    collection = get_race_control_collection()
    skey_str = str(session_key)

    existing = collection.get(where={"session_key": skey_str})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    if df_rc.empty:
        return

    df = df_rc.copy()
    if "date" in df.columns:
        df["date_str"] = df["date"].astype(str)
    else:
        df["date_str"] = ""

    ids = [f"rc_{skey_str}_{i}" for i in range(len(df))]
    documents = (
        df["message"].fillna("").tolist() if "message" in df.columns else [""] * len(df)
    )
    metadatas = [
        {
            "session_key": skey_str,
            "driver_number": str(row.get("driver_number", "")),
            "category": row.get("category", ""),
            "flag": row.get("flag", ""),
            "date_str": row.get("date_str", ""),
        }
        for _, row in df.iterrows()
    ]

    collection.add(ids=ids, documents=documents, metadatas=metadatas)


def query_race_control(
    session_key: int | str, question: str, n_results: int = 5
) -> list[dict[str, Any]]:
    collection = get_race_control_collection()
    skey_str = str(session_key)

    count = collection.count()
    if count == 0:
        return []

    results = collection.query(
        query_texts=[question],
        n_results=min(n_results, count),
        where={"session_key": skey_str},
    )

    output = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            output.append(
                {
                    "id": doc_id,
                    "message": results["documents"][0][i],
                    "session_key": meta.get("session_key", skey_str),
                    "driver_number": meta.get("driver_number", ""),
                    "category": meta.get("category", ""),
                    "flag": meta.get("flag", ""),
                    "date_str": meta.get("date_str", ""),
                    "relevance": (
                        float(results["distances"][0][i])
                        if results.get("distances")
                        else 0.0
                    ),
                }
            )
    return output
