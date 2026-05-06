# /// script
# dependencies = [
#   "chromadb>=1.0.0,<2",
#   "python-dotenv>=1.0.0,<2",
# ]
# ///
"""Build a fresh OpenFOAM ChromaDB without touching the GEOS vector DB."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
FOAM_AGENT_ROOT = Path("/home/brianliu/Foam-Agent")
DEFAULT_DB_DIR = REPO_ROOT / "data" / "openfoam_benchmark" / "chromadb_openfoam"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

COLLECTION_TUTORIALS = "openfoam_tutorials"
COLLECTION_CASES = "openfoam_cases"
COLLECTION_COMMANDS = "openfoam_commands"

load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(Path.cwd() / ".env", override=False)


@dataclass
class Chunk:
    collection: str
    identifier: str
    text: str
    metadata: dict[str, Any]


class HashEmbeddingFunction:
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


def chunk_text(text: str, *, chunk_size: int = 1800, overlap: int = 200) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(start + chunk_size - overlap, start + 1)
    return chunks


def split_on_markers(text: str, markers: tuple[str, ...]) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if any(line.startswith(marker) for marker in markers) and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [section for section in sections if section]


def load_chunks() -> list[Chunk]:
    raw_dir = FOAM_AGENT_ROOT / "database" / "raw"
    tutorials_structure = (raw_dir / "openfoam_tutorials_structure.txt").read_text(
        encoding="utf-8"
    )
    tutorials_details = (raw_dir / "openfoam_tutorials_details.txt").read_text(
        encoding="utf-8"
    )
    commands = (raw_dir / "openfoam_commands.txt").read_text(encoding="utf-8")
    command_help = (raw_dir / "openfoam_command_help.txt").read_text(encoding="utf-8")
    allrun_scripts = (raw_dir / "openfoam_allrun_scripts.txt").read_text(encoding="utf-8")

    chunks: list[Chunk] = []

    for idx, section in enumerate(split_on_markers(tutorials_structure, ("case name:", "<index>"))):
        for chunk_idx, piece in enumerate(chunk_text(section)):
            chunks.append(
                Chunk(
                    collection=COLLECTION_TUTORIALS,
                    identifier=f"tutorial-structure-{idx}-{chunk_idx}",
                    text=piece,
                    metadata={
                        "title": f"Tutorial structure {idx}",
                        "section": "tutorial_structure",
                        "kind": "tutorial_structure",
                        "source": str(raw_dir / "openfoam_tutorials_structure.txt"),
                    },
                )
            )

    for idx, section in enumerate(split_on_markers(tutorials_details, ("case name:", "<index>"))):
        for chunk_idx, piece in enumerate(chunk_text(section)):
            chunks.append(
                Chunk(
                    collection=COLLECTION_CASES,
                    identifier=f"tutorial-details-{idx}-{chunk_idx}",
                    text=piece,
                    metadata={
                        "title": f"Tutorial details {idx}",
                        "section": "tutorial_details",
                        "kind": "tutorial_details",
                        "source": str(raw_dir / "openfoam_tutorials_details.txt"),
                    },
                )
            )

    for idx, section in enumerate(split_on_markers(allrun_scripts, ("case name:", "tutorial:"))):
        for chunk_idx, piece in enumerate(chunk_text(section, chunk_size=1200, overlap=150)):
            chunks.append(
                Chunk(
                    collection=COLLECTION_CASES,
                    identifier=f"allrun-{idx}-{chunk_idx}",
                    text=piece,
                    metadata={
                        "title": f"Allrun scripts {idx}",
                        "section": "allrun_scripts",
                        "kind": "allrun_script",
                        "source": str(raw_dir / "openfoam_allrun_scripts.txt"),
                    },
                )
            )

    for name, text, source in [
        ("command_reference", commands, raw_dir / "openfoam_commands.txt"),
        ("command_help", command_help, raw_dir / "openfoam_command_help.txt"),
    ]:
        for chunk_idx, piece in enumerate(chunk_text(text, chunk_size=1400, overlap=120)):
            chunks.append(
                Chunk(
                    collection=COLLECTION_COMMANDS,
                    identifier=f"{name}-{chunk_idx}",
                    text=piece,
                    metadata={
                        "title": name,
                        "section": name,
                        "kind": name,
                        "source": str(source),
                    },
                )
            )

    return chunks


def build_embedding_function(provider: str) -> Any:
    provider = provider.lower()
    if provider == "openai":
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OpenAI/OpenRouter embedding mode requires OPENROUTER_API_KEY or OPENAI_API_KEY"
            )
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            api_base=os.environ.get("OPENROUTER_API_BASE", DEFAULT_OPENROUTER_API_BASE),
            model_name=os.environ.get(
                "OPENFOAM_OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_EMBEDDING_MODEL
            ),
        )
    return HashEmbeddingFunction()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_DIR)
    parser.add_argument(
        "--embedding-provider",
        choices=["hash", "openai"],
        default=os.environ.get("OPENFOAM_EMBEDDING_PROVIDER", "hash"),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete any existing DB at --db-dir before rebuilding.",
    )
    args = parser.parse_args()

    if args.db_dir.exists():
        if not args.force:
            raise SystemExit(f"Refusing to overwrite existing DB: {args.db_dir}")
        shutil.rmtree(args.db_dir)

    args.db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(args.db_dir))
    embedding_fn = build_embedding_function(args.embedding_provider)

    chunks = load_chunks()
    grouped: dict[str, list[Chunk]] = {
        COLLECTION_TUTORIALS: [],
        COLLECTION_CASES: [],
        COLLECTION_COMMANDS: [],
    }
    for chunk in chunks:
        grouped[chunk.collection].append(chunk)

    for collection_name, items in grouped.items():
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_fn,
        )
        batch_size = 1000
        for start in range(0, len(items), batch_size):
            batch = items[start : start + batch_size]
            collection.add(
                ids=[item.identifier for item in batch],
                documents=[item.text for item in batch],
                metadatas=[item.metadata for item in batch],
            )
        print(f"{collection_name}: {len(items)} chunks")

    print(f"Built OpenFOAM Chroma DB at {args.db_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
