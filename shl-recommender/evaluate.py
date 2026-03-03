"""
Evaluate on train set and generate predictions for test set.
"""
import json
import pandas as pd
import numpy as np
from embeddings import recommend, load_embeddings

# ---- Load your dataset ----
# Update these paths based on what's in Gen_AI_Dataset.xlsx
def load_dataset():
    xl = pd.ExcelFile("Gen_AI_Dataset.xlsx")
    print("Sheets:", xl.sheet_names)
    
    train_df = xl.parse("train")  # Adjust sheet name
    test_df = xl.parse("test")    # Adjust sheet name
    
    return train_df, test_df


def recall_at_k(predicted_urls, relevant_urls, k=10):
    """Compute Recall@K"""
    pred_top_k = predicted_urls[:k]
    hits = len(set(pred_top_k) & set(relevant_urls))
    return hits / len(relevant_urls) if relevant_urls else 0


def evaluate_train(data):
    train_df, _ = load_dataset()
    
    # Expected columns: 'query', 'relevant_assessments' or similar
    print("Train columns:", train_df.columns.tolist())
    print(train_df.head(3))
    
    # Group by query
    recalls = []
    queries = train_df["query"].unique()
    
    for q in queries:
        relevant = train_df[train_df["query"] == q]["Assessment URL"].tolist()
        results = recommend(q, top_k=10, data=data)
        predicted = [r["url"] for r in results]
        
        r_at_k = recall_at_k(predicted, relevant, k=10)
        recalls.append(r_at_k)
        print(f"  Q: {q[:60]}...")
        print(f"  Recall@10: {r_at_k:.3f} ({len(relevant)} relevant)")
    
    mean_recall = np.mean(recalls)
    print(f"\n=== Mean Recall@10: {mean_recall:.4f} ===")
    return mean_recall


def generate_predictions(data):
    _, test_df = load_dataset()
    print("Test columns:", test_df.columns.tolist())
    
    rows = []
    for q in test_df["query"].unique():
        results = recommend(q, top_k=10, data=data)
        for r in results:
            rows.append({"query": q, "Assessment_url": r["url"]})
    
    pred_df = pd.DataFrame(rows)
    pred_df.to_csv("firstname_lastname.csv", index=False)
    print(f"✅ Saved predictions: {len(pred_df)} rows for {test_df['query'].nunique()} queries")
    return pred_df


if __name__ == "__main__":
    print("Loading embeddings...")
    data = load_embeddings()
    
    print("\n=== Evaluating on Train Set ===")
    evaluate_train(data)
    
    print("\n=== Generating Test Predictions ===")
    generate_predictions(data)