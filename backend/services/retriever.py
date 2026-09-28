"""
retriever.py
------------
Module 2, Steps C & D of the roadmap: "Create embeddings -> FAISS/Chroma"
and "Retrieve the most relevant chunks".

This prototype uses scikit-learn's TF-IDF + cosine similarity as a fast,
dependency-light stand-in for a vector database (FAISS/ChromaDB), which is
exactly what a semantic vector search does at a smaller scale. Swapping in
FAISS/Chroma + real embeddings later is a drop-in replacement behind the
same `PolicyRetriever` interface -- nothing else in the app needs to change.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class PolicyRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.texts = [c["text"] for c in chunks]
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=4000)
        if self.texts:
            self.matrix = self.vectorizer.fit_transform(self.texts)
        else:
            self.matrix = None

    def retrieve(self, query, top_k=4, min_score=0.05):
        if not self.texts or self.matrix is None:
            return []
        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.matrix)[0]
        ranked = sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True)
        results = []
        for chunk, score in ranked[:top_k]:
            if score >= min_score:
                results.append({**chunk, "score": round(float(score), 3)})
        return results
