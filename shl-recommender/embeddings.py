"""
Build sentence embeddings for all assessments and save index.
Uses sentence-transformers (free, local, no API key needed).
"""
import json
import os
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"  # Fast + good quality, 384-dim

def build_text(assessment):
    """Create rich text representation for embedding"""
    parts = [
        assessment.get("name", ""),
        assessment.get("description", ""),
        " ".join(assessment.get("test_type", [])),
        f"remote: {assessment.get('remote_support', '')}",
        f"adaptive: {assessment.get('adaptive_support', '')}",
    ]
    return " | ".join(filter(None, parts))


def get_data_path(filename):
    """Get the correct path to data files, relative to the script's location."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "data", filename)


def build_embeddings():
    print("Loading assessments...")
    with open(get_data_path("shl_assessments.json")) as f:
        assessments = json.load(f)
    
    print(f"Building embeddings for {len(assessments)} assessments...")
    model = SentenceTransformer(MODEL_NAME)
    
    texts = [build_text(a) for a in assessments]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    
    data = {
        "assessments": assessments,
        "embeddings": embeddings,
        "model": MODEL_NAME
    }
    
    with open(get_data_path("embeddings.pkl"), "wb") as f:
        pickle.dump(data, f)
    
    print(f"✅ Saved embeddings.pkl ({embeddings.shape})")
    return data


def load_embeddings():
    path = get_data_path("embeddings.pkl")
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        print("embeddings.pkl missing or empty — rebuilding...")
        return build_embeddings()
    with open(path, "rb") as f:
        return pickle.load(f)


def recommend(query: str, top_k: int = 10, data=None):
    """
    Core recommendation function using cosine similarity + type balancing.
    """
    if data is None:
        data = load_embeddings()
    
    model = SentenceTransformer(data["model"])
    
    # Encode query
    query_emb = model.encode([query])[0]
    
    # Cosine similarity
    embeddings = data["embeddings"]
    scores = np.dot(embeddings, query_emb) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_emb) + 1e-10
    )
    
    # Get top candidates (2x for reranking)
    top_indices = np.argsort(scores)[::-1][:top_k * 3]
    
    candidates = []
    for idx in top_indices:
        a = data["assessments"][idx].copy()
        a["score"] = float(scores[idx])
        candidates.append(a)
    
    # Rerank for balance: ensure diversity of test types
    final = balance_recommendations(candidates, top_k)
    return final


def balance_recommendations(candidates, top_k):
    """
    Ensure balanced test type coverage.
    Strategy: greedy selection preferring type diversity.
    """
    selected = []
    type_counts = {}
    
    # First pass: take top candidate
    selected.append(candidates[0])
    for t in candidates[0].get("test_type", []):
        type_counts[t] = type_counts.get(t, 0) + 1
    
    # Second pass: balance types
    for c in candidates[1:]:
        if len(selected) >= top_k:
            break
        
        ctypes = c.get("test_type", [])
        
        # Prefer candidates with underrepresented types
        new_type = any(type_counts.get(t, 0) == 0 for t in ctypes)
        
        if new_type or len(selected) < top_k // 2:
            selected.append(c)
            for t in ctypes:
                type_counts[t] = type_counts.get(t, 0) + 1
    
    # Fill remaining with top scores if needed
    for c in candidates:
        if len(selected) >= top_k:
            break
        if c not in selected:
            selected.append(c)
    
    return selected[:top_k]


if __name__ == "__main__":
    build_embeddings()
    
    # Quick test
    print("\n=== Testing recommendations ===")
    data = load_embeddings()
    results = recommend("Java developer who collaborates with business teams", data=data)
    for r in results:
        print(f"  {r['name']} | {r['test_type']} | score={r['score']:.3f}")