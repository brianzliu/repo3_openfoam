# /// script
# dependencies = [
#   "chromadb>=1.0.0,<2",
#   "mcp>=1.0.0,<2",
#   "python-dotenv>=1.0.0,<2",
# ]
# ///
"""MCP server exposing OpenFOAM ChromaDB retrieval tools."""

from __future__ import annotations

import hashlib
import json
import os
import re
from math import sqrt
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
DEFAULT_VECTOR_DB_DIR = (
    PLUGIN_ROOT.parent / "data" / "openfoam_benchmark" / "chromadb_openfoam"
)
DEFAULT_EMBEDDING_PROVIDER = "hash"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

COLLECTION_TUTORIALS = "openfoam_tutorials"
COLLECTION_CASES = "openfoam_cases"
COLLECTION_COMMANDS = "openfoam_commands"

load_dotenv(PLUGIN_ROOT / ".env", override=False)
load_dotenv(Path.cwd() / ".env", override=False)


def _vector_db_dir() -> Path:
    explicit = os.environ.get("OPENFOAM_VECTOR_DB_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()
    return DEFAULT_VECTOR_DB_DIR.resolve()


def _embedding_function() -> Any:
    provider = os.environ.get(
        "OPENFOAM_EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER
    ).strip().lower()
    if provider == "openai":
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENFOAM_EMBEDDING_PROVIDER=openai requires OPENROUTER_API_KEY or OPENAI_API_KEY"
            )
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            api_base=os.environ.get("OPENROUTER_API_BASE", DEFAULT_OPENROUTER_API_BASE),
            model_name=os.environ.get(
                "OPENFOAM_OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_EMBEDDING_MODEL
            ),
        )
    return HashEmbeddingFunction()


class HashEmbeddingFunction:
    """Lightweight deterministic embedding for local Chroma use."""

    def __init__(self, dims: int = 256) -> None:
        self.dims = dims

    def name(self) -> str:
        return "openfoam_hash_embedding"

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dims
        tokens = re.findall(r"[A-Za-z0-9_./:+-]+", text.lower())
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dims
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in input]


class ChromaSearchBackend:
    def __init__(self) -> None:
        self.vector_db_dir = _vector_db_dir()
        self.client = chromadb.PersistentClient(path=str(self.vector_db_dir))
        self.embedding_fn = _embedding_function()
        self._collections: dict[str, Any] = {}

    def get_collection(self, name: str) -> Any:
        if name not in self._collections:
            self._collections[name] = self.client.get_collection(
                name=name,
                embedding_function=self.embedding_fn,
            )
        return self._collections[name]


def _bounded_n_results(value: int, *, default: int, maximum: int = 10) -> int:
    try:
        n_results = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(n_results, maximum))


def _format_results(results: dict[str, Any], *, preview_chars: int = 240) -> list[dict[str, Any]]:
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    formatted: list[dict[str, Any]] = []
    for index, doc in enumerate(documents):
        meta = metadatas[index] if index < len(metadatas) else {}
        distance = distances[index] if index < len(distances) else None
        preview = doc[:preview_chars] + "..." if len(doc) > preview_chars else doc
        formatted.append(
            {
                "title": meta.get("title", "Untitled"),
                "source": meta.get("source", ""),
                "section": meta.get("section", ""),
                "kind": meta.get("kind", ""),
                "distance": distance,
                "preview": preview,
            }
        )
    return formatted


mcp = FastMCP("openfoam-rag")
_backend: ChromaSearchBackend | None = None


def _get_backend() -> ChromaSearchBackend:
    global _backend
    if _backend is None:
        _backend = ChromaSearchBackend()
    return _backend


@mcp.tool()
def search_tutorials(query: str, n_results: int = 5) -> dict[str, Any]:
    """Search OpenFOAM tutorial-level guidance and directory structure chunks."""
    collection = _get_backend().get_collection(COLLECTION_TUTORIALS)
    results = collection.query(
        query_texts=[query], n_results=_bounded_n_results(n_results, default=5)
    )
    return {
        "query": query,
        "results": _format_results(results),
    }


@mcp.tool()
def search_cases(query: str, n_results: int = 5) -> dict[str, Any]:
    """Search detailed OpenFOAM case snippets and Allrun-derived context."""
    collection = _get_backend().get_collection(COLLECTION_CASES)
    results = collection.query(
        query_texts=[query], n_results=_bounded_n_results(n_results, default=5)
    )
    return {
        "query": query,
        "results": _format_results(results),
    }


@mcp.tool()
def search_commands(query: str, n_results: int = 5) -> dict[str, Any]:
    """Search OpenFOAM command help and command-reference chunks."""
    collection = _get_backend().get_collection(COLLECTION_COMMANDS)
    results = collection.query(
        query_texts=[query], n_results=_bounded_n_results(n_results, default=5)
    )
    return {
        "query": query,
        "results": _format_results(results),
    }


@mcp.tool()
def healthcheck() -> dict[str, Any]:
    """Return basic server metadata."""
    return {
        "vector_db_dir": str(_vector_db_dir()),
        "collections": [COLLECTION_TUTORIALS, COLLECTION_CASES, COLLECTION_COMMANDS],
        "embedding_provider": os.environ.get(
            "OPENFOAM_EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER
        ),
    }


if __name__ == "__main__":
    mcp.run()
