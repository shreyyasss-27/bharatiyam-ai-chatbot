import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

from bert_score import score

from sacrebleu.metrics import BLEU
from rouge_score import rouge_scorer

def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _prepare_examples(records: List[Dict[str, Any]], hyp_key: str, ref_key: str) -> tuple[List[str], List[List[str]]]:
    predictions: List[str] = []
    references: List[List[str]] = []

    for idx, record in enumerate(records, start=1):
        if hyp_key not in record:
            raise KeyError(f"Missing hypothesis key '{hyp_key}' in record #{idx}")
        if ref_key not in record:
            raise KeyError(f"Missing reference key '{ref_key}' in record #{idx}")

        hypothesis = str(record[hyp_key]).strip()
        ref_value = record[ref_key]

        if isinstance(ref_value, list):
            ref_list = [str(r).strip() for r in ref_value if str(r).strip()]
        else:
            ref_list = [str(ref_value).strip()]

        if not hypothesis:
            raise ValueError(f"Empty hypothesis encountered in record #{idx}")
        if not ref_list:
            raise ValueError(f"No reference text found in record #{idx}")

        predictions.append(hypothesis)
        references.append(ref_list)

    return predictions, references


def compute_bleu(predictions: List[str], references: List[List[str]]) -> float:
    metric = BLEU(effective_order=True)
    bleu = metric.corpus_score(predictions, list(zip(*references)))
    return float(bleu.score)


def compute_rouge(predictions: List[str], references: List[List[str]]) -> Dict[str, float]:
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    totals = {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

    for pred, ref_list in zip(predictions, references):
        best_scores = {key: 0.0 for key in totals}
        for reference in ref_list:
            scores = scorer.score(reference, pred)
            for key in totals:
                best_scores[key] = max(best_scores[key], scores[key].fmeasure)
        for key in totals:
            totals[key] += best_scores[key]

    count = len(predictions)
    return {key: (totals[key] / count) * 100.0 for key in totals}


def compute_precision_recall_f1(predictions: List[str], references: List[List[str]]) -> Dict[str, float]:
    scorer = rouge_scorer.RougeScorer(["rouge1"], use_stemmer=True)
    precisions, recalls, f1s = [], [], []
    for pred, ref_list in zip(predictions, references):
        best = {'precision': 0.0, 'recall': 0.0, 'fmeasure': 0.0}
        for reference in ref_list:
            score = scorer.score(reference, pred)["rouge1"]
            if score.fmeasure > best['fmeasure']:
                best = {'precision': score.precision, 'recall': score.recall, 'fmeasure': score.fmeasure}
        precisions.append(best['precision'])
        recalls.append(best['recall'])
        f1s.append(best['fmeasure'])
    count = len(predictions)
    return {
        'precision': sum(precisions) / count * 100.0,
        'recall': sum(recalls) / count * 100.0,
        'f1': sum(f1s) / count * 100.0
    }

def compute_recall_at_k(records: List[Dict[str, Any]], k: int = 5) -> float:
    # Each record should have 'retrieved_chunks' and 'relevant_chunks' as lists of IDs
    recalls = []
    for rec in records:
        retrieved = set(rec.get('retrieved_chunks', [])[:k])
        relevant = set(rec.get('relevant_chunks', []))
        if not relevant:
            continue
        recall = len(retrieved & relevant) / len(relevant)
        recalls.append(recall)
    return (sum(recalls) / len(recalls) * 100.0) if recalls else 0.0


def compute_bertscore(predictions: List[str], references: List[List[str]], lang: str = "en") -> dict:
    # BERTScore expects a list of strings for references, so we use the first reference for each sample
    single_references = [refs[0] if refs else "" for refs in references]
    P, R, F1 = score(predictions, single_references, lang=lang, verbose=False)
    return {
        "bertscore_precision": float(P.mean().item()) * 100.0,
        "bertscore_recall": float(R.mean().item()) * 100.0,
        "bertscore_f1": float(F1.mean().item()) * 100.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute BLEU and ROUGE scores for model outputs.")
    parser.add_argument("jsonl_path", type=Path, help="Path to JSONL file with references and predictions")
    parser.add_argument("--hyp-key", default="prediction", help="JSON key containing the model output")
    parser.add_argument("--ref-key", default="reference", help="JSON key containing the reference text or list")
    parser.add_argument("--save", type=Path, default=None, help="Optional path to save scores as JSON")
    parser.add_argument("--recall-at-k", type=int, default=5, help="k for Recall@k if chunk info present")
    parser.add_argument("--bertscore-lang", default="en", help="Language code for BERTScore model (default: en)")
    args = parser.parse_args()

    records = _load_jsonl(args.jsonl_path)
    predictions, references = _prepare_examples(records, args.hyp_key, args.ref_key)

    bleu = compute_bleu(predictions, references)
    rouge = compute_rouge(predictions, references)
    prf = compute_precision_recall_f1(predictions, references)
    bertscore = compute_bertscore(predictions, references, lang=args.bertscore_lang)
    recall_at_k = compute_recall_at_k(records, k=args.recall_at_k)

    results = {
        "bleu": bleu,
        "rouge1": rouge["rouge1"],
        "rouge2": rouge["rouge2"],
        "rougeL": rouge["rougeL"],
        "precision": prf["precision"],
        "recall": prf["recall"],
        "f1": prf["f1"],
        "recall@k": recall_at_k,
        "samples": len(predictions),
        **bertscore,
    }

    print("\n=== Evaluation Summary ===")
    print(f"Samples: {results['samples']}")
    print(f"BLEU:   {results['bleu']:.2f}")
    print(f"ROUGE-1 F1: {results['rouge1']:.2f}")
    print(f"ROUGE-2 F1: {results['rouge2']:.2f}")
    print(f"ROUGE-L F1: {results['rougeL']:.2f}")
    print(f"Precision: {results['precision']:.2f}")
    print(f"Recall:    {results['recall']:.2f}")
    print(f"F1:        {results['f1']:.2f}")
    print(f"Recall@{args.recall_at_k}: {results['recall@k']:.2f}")
    print(f"BERTScore Precision: {results['bertscore_precision']:.2f}")
    print(f"BERTScore Recall:    {results['bertscore_recall']:.2f}")
    print(f"BERTScore F1:        {results['bertscore_f1']:.2f}")

    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        with args.save.open("w", encoding="utf-8") as out_file:
            json.dump(results, out_file, indent=2)
        print(f"\nSaved results to {args.save}")


if __name__ == "__main__":
    main()
