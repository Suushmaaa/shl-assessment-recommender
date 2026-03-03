# SHL Assessment Recommender: Solution Approach

## Project Overview

This project builds an intelligent recommendation system for SHL's catalog of 377+ assessments. The goal is to help HR professionals find relevant assessments by entering natural language job descriptions or queries.

---

## Solution Components

### 1. Web Scraper (scraper_robust.py)
- Crawls SHL's product catalog across multiple pages
- Extracts: name, URL, description, test type, remote/adaptive support, duration
- Handles pagination with 12 items per page
- Enriches each assessment with detail page information

### 2. Embedding System (embeddings.py)
- Uses sentence-transformers model `all-MiniLM-L6-v2` (384-dimensional vectors)
- Creates rich text representation for each assessment combining name, description, test types, and metadata
- Stores embeddings in pickle format for fast loading

### 3. Recommendation Algorithm
- Encodes user query into same embedding space
- Computes cosine similarity between query and all assessments
- Retrieves top 30 candidates for reranking
- Applies type-balancing to ensure diverse test type coverage
- Returns top 10 recommendations

### 4. REST API (api.py)
- FastAPI-based endpoints: `/health` and `/recommend`
- Accepts natural language queries or job posting URLs
- Extracts content from URLs if a URL is provided as query

### 5. Frontend (frontend/index.html)
- Clean HTML/CSS interface
- Accepts queries or URLs
- Displays recommendations with metadata badges

---

## Key Technical Decisions

| Decision | Rationale |
|----------|------------|
| Semantic embeddings | Captures intent beyond keyword matching |
| Type-balanced reranking | Ensures diverse test type recommendations |
| Local embedding model | No API costs, fast inference |
| URL content extraction | Enables using job posting URLs as input |

---

## Pipeline Execution

```
bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Scrape assessment data
python scraper_robust.py

# 3. Build embeddings
python embeddings.py

# 4. Start API
uvicorn api:app --reload --port 8000

# 5. Open frontend in browser
# 6. Evaluate
python evaluate.py
```

---

## Evaluation

The system evaluates using Recall@K on the training set by comparing predicted assessment URLs against known relevant assessments. Test predictions are saved to CSV for submission.

---

## Conclusion

This solution provides a complete pipeline from data collection to recommendation delivery, using semantic search to match job requirements with appropriate assessments. The type-balanced reranking ensures diverse, practical recommendations for recruiters.
