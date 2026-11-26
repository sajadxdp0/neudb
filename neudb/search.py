"""Vector and text search helpers used by :class:`~neudb.table.Table`."""

import heapq
import math
from collections.abc import Iterable, Sequence


def validate_vector(vector: Sequence[float], label: str) -> None:
    if not isinstance(vector, Sequence) or isinstance(vector, (str, bytes)):
        raise ValueError(f"{label} must be a sequence of numbers.")
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{label} must contain only finite numbers.")
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError(f"{label} must contain only finite numbers.")


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    if len(vec_a) != len(vec_b):
        raise ValueError("Vectors must be the same length.")
    norm_a = math.hypot(*vec_a)
    norm_b = math.hypot(*vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    similarity = math.fsum((a / norm_a) * (b / norm_b) for a, b in zip(vec_a, vec_b, strict=True))
    return max(-1.0, min(1.0, similarity))


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Return cosine similarity for equal-length finite vectors.

    Zero-norm vectors have similarity ``0.0``. Invalid values and mismatched
    dimensions raise :class:`ValueError` instead of leaking ``TypeError`` or
    returning NaN.
    """
    validate_vector(vec_a, "Vector A")
    validate_vector(vec_b, "Vector B")
    return _cosine_similarity(vec_a, vec_b)


def rank_by_similarity(
    records: Iterable[dict],
    field: str,
    query_vector: Sequence[float],
    top_k: int,
) -> list[dict]:
    """Return up to ``top_k`` compatible records, best matches first."""
    if top_k < 1:
        return []
    validate_vector(query_vector, "Query vector")
    results: list[tuple[float, int, dict]] = []
    for index, record in enumerate(records):
        vec = record.get(field)
        if not isinstance(vec, list):
            continue
        try:
            validate_vector(vec, "Record vector")
            similarity = _cosine_similarity(query_vector, vec)
        except ValueError:
            continue
        results.append((similarity, index, record))
    return [record for _, _, record in heapq.nlargest(top_k, results, key=lambda item: item[0])]


def filter_by_text(
    records: Iterable[dict],
    field: str,
    query: str,
    top_k: int,
) -> list[dict]:
    """Return up to ``top_k`` case-insensitive substring matches."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    query_text = query.casefold()
    if not query_text or top_k < 1:
        return []
    results = []
    for record in records:
        value = record.get(field)
        if value is not None and query_text in str(value).casefold():
            results.append(record)
            if len(results) == top_k:
                break
    return results
