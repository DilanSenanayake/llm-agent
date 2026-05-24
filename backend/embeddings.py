# Sentence-transformers embeddings (all-MiniLM-L6-v2) for LangChain.

from __future__ import annotations

import os
from typing import List, Optional

import numpy as np
from langchain_core.embeddings import Embeddings

MODEL_NAME = "all-MiniLM-L6-v2"


# LangChain-compatible embeddings using sentence-transformers.
class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str = MODEL_NAME) -> None:
        from sentence_transformers import SentenceTransformer

        # Allow offline cache dir via env (optional)
        cache = os.getenv("SENTENCE_TRANSFORMERS_HOME")
        self._model = SentenceTransformer(
            model_name,
            cache_folder=cache,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if isinstance(vectors, np.ndarray):
            return vectors.astype(float).tolist()
        return [np.asarray(v, dtype=float).tolist() for v in vectors]

    def embed_query(self, text: str) -> List[float]:
        vec = self._model.encode(
            [text],
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vec[0], dtype=float).tolist()


_embeddings_instance: Optional[MiniLMEmbeddings] = None


# Reuse one embedding model instance (heavy to reload).
def get_embeddings() -> MiniLMEmbeddings:
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = MiniLMEmbeddings()
    return _embeddings_instance
