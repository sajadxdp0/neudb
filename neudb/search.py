"""Vector and text search helpers used by :class:`~neudb.table.Table`."""

import math
from typing import Iterable, List, Tuple


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Return the cosine similarity between two vectors of equal length."""
    if len(vec_a) != len(vec_b):
        raise ValueError("Vectors must be the same length.")
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_by_similarity(
    records: Iterable[dict],
    field: str,
    query_vector: List[float],
    top_k: int,
) -> List[dict]:
    """Return up to top_k records with a compatible vector, best matches first."""
    results: List[Tuple[float, dict]] = []
    for record in records:
        vec = record.get(field)
        if vec is not None and isinstance(vec, list):
            try:
                sim = cosine_similarity(query_vector, vec)
            except ValueError:
                continue
            results.append((sim, record))
    results.sort(key=lambda item: item[0], reverse=True)
    return [record for _, record in results[:top_k]]


def filter_by_text(
    records: Iterable[dict],
    field: str,
    query: str,
    top_k: int,
) -> List[dict]:
    """Return up to top_k records whose field contains query, case-insensitive."""
    query_text = query.lower()
    if not query_text:
        return []
    results = []
    for record in records:
        value = record.get(field)
        if value is not None and query_text in str(value).lower():
            results.append(record)
    return results[:top_k]
