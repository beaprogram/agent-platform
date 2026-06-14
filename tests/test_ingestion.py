"""Unit tests for the ingestion chunker (no AWS or network calls)."""


def test_chunk_splits_long_text(ing):
    chunks = ing._chunk("word " * 500)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)


def test_chunk_empty_returns_nothing(ing):
    assert ing._chunk("   \n  ") == []


def test_chunk_short_text_single_piece(ing):
    chunks = ing._chunk("A short sentence.")
    assert chunks == ["A short sentence."]
