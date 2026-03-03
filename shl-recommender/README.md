# SHL Assessment Recommendation System

## Setup
```bash
pip install -r requirements.txt
mkdir data

# Step 1: Scrape catalog
python scraper_robust.py

# Step 2: Build embeddings
python embeddings.py

# Step 3: Run API
uvicorn api:app --reload --port 8000

# Step 4: Open frontend
# Open frontend/index.html in browser

# Step 5: Evaluate + predictions
python evaluate.py
```

## Architecture
- **Scraper**: BeautifulSoup crawls SHL catalog (377+ tests)
- **Embeddings**: sentence-transformers `all-MiniLM-L6-v2` for semantic search
- **Retrieval**: Cosine similarity + type-balanced reranking
- **API**: FastAPI with `/health` and `/recommend` endpoints
- **Frontend**: Vanilla HTML/JS