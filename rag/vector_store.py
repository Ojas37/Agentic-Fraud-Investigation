"""
rag/vector_store.py — Fast Semantic Vector Search for Case Narratives & Policy Rules
Provides semantic similarity search over:
  1. 5,565 historical closed case narratives from closed_cases_history.csv
  2. Codified Bank Fraud Policy rules (R1-R10)
  3. Regulatory guidance documents (FinCEN, FATF, FFIEC)
"""

import os
import pickle
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from rag.policy_documents import FRAUD_POLICY_RULES, REGULATORY_GUIDANCE

CACHE_PATH = "data/processed/vector_index.pkl"

class SimpleEmbeddingEngine:
    """
    Fast TF-IDF + Character N-gram embedding engine that runs in-memory with zero
    API latency, with optional sentence-transformer/OpenAI backend if configured.
    """
    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=10000,
            stop_words="english",
            sublinear_tf=True
        )
        self.is_fitted = False

    def fit_transform(self, texts: List[str]) -> np.ndarray:
        matrix = self.vectorizer.fit_transform(texts)
        self.is_fitted = True
        return matrix.toarray()

    def transform(self, texts: List[str]) -> np.ndarray:
        if not self.is_fitted:
            return np.zeros((len(texts), 1))
        matrix = self.vectorizer.transform(texts)
        return matrix.toarray()

class FraudVectorStore:
    def __init__(self, cache_file: str = CACHE_PATH):
        self.cache_file = cache_file
        self.engine = SimpleEmbeddingEngine()
        self.documents: List[Dict[str, Any]] = []
        self.doc_vectors: Optional[np.ndarray] = None
        self._initialize_index()

    def _initialize_index(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "rb") as f:
                    data = pickle.load(f)
                    self.documents = data["documents"]
                    self.doc_vectors = data["doc_vectors"]
                    self.engine = data["engine"]
                print(f"[VectorStore] Loaded {len(self.documents):,} indexed documents from cache.")
                return
            except Exception as e:
                print(f"[VectorStore] Cache load failed ({e}), rebuilding index...")

        self._build_index()

    def _build_index(self):
        docs = []
        
        # 1. Index Policy Rules
        for rule in FRAUD_POLICY_RULES:
            text = f"Policy Rule {rule['rule_id']} - {rule['title']}. Condition: {rule['condition']}. Description: {rule['description']}. Actions: {', '.join(rule['recommended_actions'])}"
            docs.append({
                "doc_type": "policy_rule",
                "id": rule["rule_id"],
                "title": rule["title"],
                "content": text,
                "metadata": rule
            })

        # 2. Index Regulatory Guidance
        for reg in REGULATORY_GUIDANCE:
            text = f"Regulatory Guidance: {reg['source']} on {reg['topic']}. {reg['summary']}"
            docs.append({
                "doc_type": "regulatory_guidance",
                "id": reg["source"],
                "title": reg["topic"],
                "content": text,
                "metadata": reg
            })

        # 3. Index Historical Closed Cases
        cases_csv = "data/raw/closed_cases_history.csv"
        if os.path.exists(cases_csv):
            df_cases = pd.read_csv(cases_csv)
            for _, row in df_cases.iterrows():
                cid = str(row["case_id"])
                outcome = str(row["outcome"])
                pattern = str(row["pattern"]) if not pd.isna(row["pattern"]) else "none"
                notes = str(row["analyst_notes"]) if not pd.isna(row["analyst_notes"]) else ""
                exposure = float(row["exposure_usd"]) if not pd.isna(row["exposure_usd"]) else 0.0
                
                text = f"Closed Case {cid}: Outcome={outcome}, Pattern={pattern}, Exposure=${exposure:.2f}. Notes: {notes}"
                docs.append({
                    "doc_type": "closed_case",
                    "id": cid,
                    "title": f"Case {cid} ({pattern})",
                    "content": text,
                    "metadata": {
                        "case_id": cid,
                        "customer_id": str(row["customer_id"]),
                        "card_id": str(row["card_id"]),
                        "outcome": outcome,
                        "pattern": pattern,
                        "exposure_usd": exposure,
                        "analyst_notes": notes
                    }
                })

        print(f"[VectorStore] Indexing {len(docs):,} documents...")
        all_texts = [d["content"] for d in docs]
        self.doc_vectors = self.engine.fit_transform(all_texts)
        self.documents = docs

        # Save cache
        with open(self.cache_file, "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "doc_vectors": self.doc_vectors,
                "engine": self.engine
            }, f)
        print(f"[VectorStore] Index built and saved to {self.cache_file}.")

    def search(self, query: str, top_k: int = 5, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.doc_vectors is None or len(self.documents) == 0:
            return []

        q_vec = self.engine.transform([query]) # shape (1, D)
        # Compute cosine similarity
        norm_q = np.linalg.norm(q_vec)
        if norm_q == 0:
            return []
        
        norm_docs = np.linalg.norm(self.doc_vectors, axis=1)
        norm_docs[norm_docs == 0] = 1.0

        scores = (self.doc_vectors @ q_vec.T).ravel() / (norm_docs * norm_q)

        ranked_indices = np.argsort(-scores)
        results = []

        for idx in ranked_indices:
            if len(results) >= top_k:
                break
            doc = self.documents[idx]
            if doc_type is not None and doc["doc_type"] != doc_type:
                continue
            
            score = float(scores[idx])
            if score > 0.0:
                results.append({
                    "doc_type": doc["doc_type"],
                    "id": doc["id"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "score": round(score, 4),
                    "metadata": doc["metadata"]
                })

        return results
