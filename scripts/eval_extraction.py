"""Score app/services/extraction.py against eval/extraction_gold.jsonl (agent-drafted labels, see eval/README.md).

Usage (from the repo root): python scripts/eval_extraction.py
Makes one OpenRouter call per company with the key and model in .env, and writes docs/extraction_eval.md.
"""

import asyncio
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from app.services import extraction  # noqa: E402

GOLD = os.path.join(ROOT, "eval", "extraction_gold.jsonl")
FIELDS = {"commodities": "commodities", "sourcing_countries": "regions", "operational_countries": "operational_regions"}


def predicted(result) -> dict[str, set[str]]:
    return {field: {item["name"] for item in getattr(result, attr)} for field, attr in FIELDS.items()}


def score(rows, preds) -> dict:
    """Micro precision/recall/F1 and exact-set match per field."""
    out = {}
    for field in FIELDS:
        tp = fp = fn = exact = 0
        for row, pred in zip(rows, preds):
            gold, got = set(row["expected"][field]), pred[field]
            tp, fp, fn = tp + len(gold & got), fp + len(got - gold), fn + len(gold - got)
            exact += gold == got
        p = tp / (tp + fp) if tp + fp else None
        r = tp / (tp + fn) if tp + fn else None
        f1 = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
        out[field] = {"p": p, "r": r, "f1": f1, "exact": exact / len(rows), "tp": tp, "fp": fp, "fn": fn}
    return out


def _fmt(x):
    return "–" if x is None else f"{x:.2f}"


async def main():
    with open(GOLD, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    keyword_extract = extraction._fallback_extract_entities
    fell_back = []

    def spy(text):
        fell_back.append(True)
        return keyword_extract(text)

    extraction._fallback_extract_entities = spy  # count silent LLM fallbacks instead of scoring them as LLM output
    llm_preds, fallback_flags = [], []
    for row in rows:
        before = len(fell_back)
        llm_preds.append(predicted(await extraction.extract_entities(row["text"])))
        fallback_flags.append(len(fell_back) > before)
        print(f"{row['company']}: {'FALLBACK ' if fallback_flags[-1] else ''}{llm_preds[-1]}")
    extraction._fallback_extract_entities = keyword_extract

    keyword_preds = [predicted(keyword_extract(row["text"])) for row in rows]
    systems = {f"LLM ({extraction.OPENROUTER_MODEL})": score(rows, llm_preds),
               "Keyword fallback (no LLM)": score(rows, keyword_preds)}

    swaps_so = sum(len(set(r["expected"]["sourcing_countries"]) & p["operational_countries"]) for r, p in zip(rows, llm_preds))
    swaps_os = sum(len(set(r["expected"]["operational_countries"]) & p["sourcing_countries"]) for r, p in zip(rows, llm_preds))

    lines = [
        "# LLM extraction eval",
        "",
        "> **Provisional.** The gold labels in `eval/extraction_gold.jsonl` were drafted by an AI agent and have not",
        "> been reviewed by a person yet. Treat these numbers as a first pass, not as a measured accuracy.",
        "",
        f"Run on {date.today().isoformat()} with `python scripts/eval_extraction.py`: {len(rows)} companies, one",
        f"OpenRouter call each ({sum(fallback_flags)} fell back to keyword matching). Each text is an excerpt of",
        "the CSR page `CSRScraper.scrape()` returned: a 120-character window around every commodity or country",
        "mention, labelled or not (see `eval/README.md`). Scores are micro-averaged over all companies; *exact* is",
        "the share of companies whose predicted set equals the gold set.",
        "",
        "Excerpts are harder than the full pages production sees: a list of countries keeps its names but loses",
        "the page around it. Olam's contact-form country dropdown is the main case; on the full pages (same day,",
        "same labels, text not published) the LLM scored operational_countries P 0.74 / R 0.81 and",
        "sourcing_countries P 0.58 / R 1.00.",
        "",
        "| System | Field | Precision | Recall | F1 | Exact | TP / FP / FN |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, fields in systems.items():
        for field, m in fields.items():
            lines.append(f"| {name} | {field} | {_fmt(m['p'])} | {_fmt(m['r'])} | {_fmt(m['f1'])} | "
                         f"{m['exact']:.2f} | {m['tp']} / {m['fp']} / {m['fn']} |")
    lines += [
        "",
        "The keyword fallback cannot tell sourcing from operations: every country it finds counts as sourcing.",
        "",
        f"**Sourcing vs operations mix-ups (LLM):** {swaps_so} gold sourcing countries were returned as operational",
        f"(so they drop out of the risk score), and {swaps_os} gold operational countries were returned as sourcing.",
        "",
        "## Per company (LLM)",
        "",
        "Missed = in the gold labels but not predicted; extra = predicted but not in the gold labels.",
        "",
        "| Company | Field | Missed | Extra |",
        "|---|---|---|---|",
    ]
    for row, pred, fb in zip(rows, llm_preds, fallback_flags):
        label = row["company"] + (" (fallback)" if fb else "")
        for field in FIELDS:
            gold = set(row["expected"][field])
            missed, extra = sorted(gold - pred[field]), sorted(pred[field] - gold)
            if missed or extra:
                lines.append(f"| {label} | {field} | {', '.join(missed) or '–'} | {', '.join(extra) or '–'} |")
    lines.append("")

    with open(os.path.join(ROOT, "docs", "extraction_eval.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote docs/extraction_eval.md")


if __name__ == "__main__":
    asyncio.run(main())
