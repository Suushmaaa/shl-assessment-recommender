"""
FastAPI backend for SHL Assessment Recommender
Run: uvicorn api:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import re

from embeddings import recommend, load_embeddings

app = FastAPI(title="SHL Assessment Recommender", version="1.0.0")

# Allow all origins for demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load embeddings at startup
print("Loading embeddings...")
try:
    EMBED_DATA = load_embeddings()
    print(f"✅ Loaded {len(EMBED_DATA['assessments'])} assessments")
except Exception as e:
    print(f"⚠️ Could not load embeddings: {e}")
    EMBED_DATA = None


class QueryRequest(BaseModel):
    query: str


class Assessment(BaseModel):
    url: str
    name: str
    adaptive_support: str
    description: str
    duration: int
    remote_support: str
    test_type: List[str]


class RecommendResponse(BaseModel):
    recommended_assessments: List[Assessment]


def extract_url_content(url: str) -> str:
    """Fetch JD text from a URL"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:3000]  # Limit length
    except Exception as e:
        return url  # Fall back to using URL as query


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/recommend", response_model=RecommendResponse)
def get_recommendations(request: QueryRequest):
    if EMBED_DATA is None:
        raise HTTPException(status_code=503, detail="Embedding data not loaded")
    
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Check if query is a URL
    if re.match(r'https?://', query):
        print(f"Fetching URL: {query}")
        query = extract_url_content(query)
    
    # Get recommendations
    results = recommend(query, top_k=10, data=EMBED_DATA)
    
    # Format response
    assessments = []
    for r in results:
        assessments.append(Assessment(
            url=r.get("url", ""),
            name=r.get("name", ""),
            adaptive_support=r.get("adaptive_support", "No"),
            description=r.get("description", "")[:300],
            duration=r.get("duration", 0),
            remote_support=r.get("remote_support", "No"),
            test_type=r.get("test_type", [])
        ))
    
    return RecommendResponse(recommended_assessments=assessments)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)