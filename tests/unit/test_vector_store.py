import pytest

from app.services.vector_store import cosine_similarity


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1.0, 0.0, 1.0], [1.0, 0.0, 1.0]) == pytest.approx(1.0)


def test_cosine_similarity_mismatched_dimensions_is_zero():
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0
