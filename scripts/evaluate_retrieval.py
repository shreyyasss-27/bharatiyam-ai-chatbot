#!/usr/bin/env python3
"""Evaluate Bhartiyam's retrieval pipeline using precision/recall/F1.

This utility expects a JSONL dataset where each line looks like:

{"query": "Who was Bhishma?", "relevant": ["mahabharata.txt|page=10", "mahabharata.txt|page=11"]}

Each entry must contain:
  * "query" (str) – user question to test
  * "relevant" (list) – items considered ground-truth positives. Each item can be
        - a string identifier such as "source|page=4|chunk=2"
        - a dict containing metadata keys (e.g., {"source": "mahabharata.txt", "page": 4})
The script will compare retrieved chunk metadata against these identifiers and compute
confusion-matrix counts plus precision/recall/F1 (micro-averaged across queries).

Example usage:
    python scripts/evaluate_retrieval.py \
        --dataset data/eval/queries.jsonl \
        --top-k 5 \
        --fields source page chunk
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from dotenv import load_dotenv

# Ensure project modules can be imported when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.embedding_store import VectorStore  # noqa: E402


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL dataset of queries and relevant document identifiers."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {lineno}: {exc}") from exc
            if "query" not in record or not isinstance(record["query"], str):
                raise ValueError(f"Missing or invalid 'query' on line {lineno}")
            if "relevant" not in record or not isinstance(record["relevant"], list):
                raise ValueError(f"Missing or invalid 'relevant' list on line {lineno}")
            records.append(record)
    if not records:
        raise ValueError("Dataset is empty; add at least one query entry.")
    return records


def make_doc_key(metadata: Dict[str, Any], key_fields: Iterable[str]) -> str:
    """Create a stable identifier string from metadata using the selected fields."""
    if not isinstance(metadata, dict):
        return ""
    parts: List[str] = []
    for field in key_fields:
        value = metadata.get(field)
        if value is None:
            continue
        parts.append(f"{field}={value}")
    return "|".join(parts).lower()


def parse_relevant(entries: Iterable[Any], key_fields: Iterable[str]) -> Set[str]:
    """Normalise dataset 'relevant' entries into document keys."""
    keys: Set[str] = set()
    for item in entries:
        if isinstance(item, str):
            key = item.strip().lower()
        elif isinstance(item, dict):
            key = make_doc_key(item, key_fields)
        else:
            raise ValueError(f"Unsupported relevant entry type: {type(item)}")
        if key:
            keys.add(key)
    return keys


def compute_metrics(tp: int, fp: int, fn: int, tn: int) -> Dict[str, float]:
    """Return precision/recall/F1/accuracy given confusion-matrix counts."""
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def collect_corpus_keys(vector_store: VectorStore, key_fields: Iterable[str]) -> Set[str]:
    """Gather identifiers for every chunk stored in the FAISS-backed docstore."""
    if vector_store.vector_store is None:
        raise RuntimeError("Vector store is not loaded; call load_index() first.")

    docstore = getattr(vector_store.vector_store, "docstore", None)
    if docstore is None:
        raise RuntimeError("Loaded FAISS store does not expose a docstore.")

    corpus_keys: Set[str] = set()
    for doc in docstore._dict.values():  # type: ignore[attr-defined]
        metadata = getattr(doc, "metadata", {})
        key = make_doc_key(metadata, key_fields)
        if key:
            corpus_keys.add(key)
    if not corpus_keys:
        raise RuntimeError("No corpus metadata keys could be derived; check key fields.")
    return corpus_keys


def evaluate(dataset_path: Path, top_k: int, key_fields: List[str], model_name: str) -> None:
    load_dotenv()

    vector_store = VectorStore(model_name=model_name)
    if not vector_store.load_index():
        raise RuntimeError("FAISS index not found. Build the index before evaluation.")

    corpus_keys = collect_corpus_keys(vector_store, key_fields)
    corpus_size = len(corpus_keys)

    dataset = load_dataset(dataset_path)

    totals = Counter(tp=0, fp=0, fn=0, tn=0)
    per_query_rows: List[Dict[str, Any]] = []

    for record in dataset:
        query = record["query"].strip()
        ground_truth = parse_relevant(record["relevant"], key_fields)

        retrieved_docs = vector_store.similarity_search(query, k=top_k)
        predicted: Set[str] = set()
        for doc in retrieved_docs:
            key = make_doc_key(doc.get("metadata", {}), key_fields)
            if key:
                predicted.add(key)

        tp = len(predicted & ground_truth)
        fp = len(predicted - ground_truth)
        fn = len(ground_truth - predicted)
        union_size = len(predicted) + len(ground_truth) - tp
        tn = max(corpus_size - union_size, 0)

        totals.update(tp=tp, fp=fp, fn=fn, tn=tn)

        metrics = compute_metrics(tp, fp, fn, tn)
        per_query_rows.append({
            "query": query,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            **metrics,
        })

    aggregate_metrics = compute_metrics(totals["tp"], totals["fp"], totals["fn"], totals["tn"])

    print("Evaluation complete\n====================")
    print(f"Queries evaluated: {len(dataset)}")
    print(f"Corpus size (unique keys): {corpus_size}")
    print()
    print("Micro-averaged metrics:")
    for name, value in aggregate_metrics.items():
        print(f"  {name:>9}: {value:.4f}")
    print()

    print("Per-query breakdown (precision, recall, F1):")
    for row in per_query_rows:
        print(f"- {row['query']}")
        print(
            f"    TP={row['tp']} FP={row['fp']} FN={row['fn']} TN={row['tn']} | "
            f"precision={row['precision']:.4f} recall={row['recall']:.4f} f1={row['f1']:.4f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval metrics for Bhartiyam.")
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Path to JSONL file containing evaluation queries.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(os.getenv("EVAL_TOP_K", "5")),
        help="Number of chunks to retrieve per query (default: 5).",
    )
    parser.add_argument(
        "--fields",
        nargs="+",
        default=["source", "page", "chunk"],
        help="Metadata fields that identify a unique chunk (default: source page chunk).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
        help="Embedding model name (overrides EMBED_MODEL env var if supplied).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        evaluate(args.dataset, args.top_k, args.fields, args.model)
    except Exception as exc:  # pragma: no cover - surfaced to CLI
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        sys.exit(1)
