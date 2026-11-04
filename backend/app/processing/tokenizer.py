"""Load and validate the pinned tokenizer for TXT processing."""

import hashlib
import os
from pathlib import Path

from tokenizers import Tokenizer
from tokenizers import __version__ as tokenizers_version

TOKENIZER_VERSION = "0.23.3"

TOKENIZER_SHA256 = "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"


def load_tokenizer() -> Tokenizer:
    """Load the local tokenizer after validating its version and SHA-256."""

    if tokenizers_version != TOKENIZER_VERSION:
        raise RuntimeError(f"Expected tokenizers=={TOKENIZER_VERSION}, got {tokenizers_version}")

    default_dir = Path(__file__).resolve().parents[2] / "models" / "multilingual-e5-small"

    tokenizer_dir = Path(os.environ.get("FINDOCS_TOKENIZER_DIR", str(default_dir))).expanduser()

    tokenizer_path = tokenizer_dir / "tokenizer.json"

    try:
        tokenizer_bytes = tokenizer_path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"Tokenizer file is missing or unreadable: {tokenizer_path}") from exc

    actual_sha256 = hashlib.sha256(tokenizer_bytes).hexdigest()

    if actual_sha256 != TOKENIZER_SHA256:
        raise RuntimeError(f"Tokenizer SHA-256 mismatch: {actual_sha256}")

    try:
        return Tokenizer.from_file(str(tokenizer_path))
    except Exception as exc:
        raise RuntimeError(f"Failed to load tokenizer: {tokenizer_path}") from exc
