
"""Tests for loading and validating the pinned TXT tokenizer."""

import hashlib

import pytest

import app.processing.tokenizer as tokenizer_module


def test_load_valid_tokenizer():
    """Load the pinned tokenizer from its default location."""

    tokenizer = tokenizer_module.load_tokenizer()

    encoding = tokenizer.encode(
        "Привет, FinDocs!",
        add_special_tokens=False,
    )

    assert len(encoding.ids) > 0
    assert len(encoding.ids) == len(encoding.offsets)


def test_missing_tokenizer_file(tmp_path, monkeypatch):
    """Fail when tokenizer.json does not exist."""

    monkeypatch.setenv(
        "FINDOCS_TOKENIZER_DIR",
        str(tmp_path),
    )

    with pytest.raises(
        RuntimeError,
        match="missing or unreadable",
    ):
        tokenizer_module.load_tokenizer()


def test_invalid_tokenizer_checksum(tmp_path, monkeypatch):
    """Reject a tokenizer file with an incorrect SHA-256."""

    tokenizer_path = tmp_path / "tokenizer.json"
    tokenizer_path.write_text(
        '{"invalid": true}',
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "FINDOCS_TOKENIZER_DIR",
        str(tmp_path),
    )

    with pytest.raises(
        RuntimeError,
        match="SHA-256 mismatch",
    ):
        tokenizer_module.load_tokenizer()


def test_invalid_tokenizer_version(monkeypatch):
    """Reject an unsupported tokenizers library version."""

    monkeypatch.setattr(
        tokenizer_module,
        "tokenizers_version",
        "0.0.0",
    )

    with pytest.raises(
        RuntimeError,
        match="Expected tokenizers",
    ):
        tokenizer_module.load_tokenizer()


def test_invalid_tokenizer_format(tmp_path, monkeypatch):
    """Reject a file with a valid checksum but invalid format."""

    invalid_content = b"not a tokenizer"

    tokenizer_path = tmp_path / "tokenizer.json"
    tokenizer_path.write_bytes(invalid_content)

    monkeypatch.setenv(
        "FINDOCS_TOKENIZER_DIR",
        str(tmp_path),
    )

    monkeypatch.setattr(
        tokenizer_module,
        "TOKENIZER_SHA256",
        hashlib.sha256(invalid_content).hexdigest(),
    )

    with pytest.raises(
        RuntimeError,
        match="Failed to load tokenizer",
    ):
        tokenizer_module.load_tokenizer()
