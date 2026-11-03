# LLM extraction eval

> **Provisional.** The gold labels in `eval/extraction_gold.jsonl` were drafted by an AI agent and have not
> been reviewed by a person yet. Treat these numbers as a first pass, not as a measured accuracy.

Run on 2026-11-03 with `python scripts/eval_extraction.py`: 20 companies, one
OpenRouter call each (0 fell back to keyword matching). Each text is an excerpt of
the CSR page `CSRScraper.scrape()` returned: a 120-character window around every commodity or country
mention, labelled or not (see `eval/README.md`). Scores are micro-averaged over all companies; *exact* is
the share of companies whose predicted set equals the gold set.

Excerpts are harder than the full pages production sees: a list of countries keeps its names but loses
the page around it. Olam's contact-form country dropdown is the main case; on the full pages (same day,
same labels, text not published) the LLM scored operational_countries P 0.74 / R 0.81 and
sourcing_countries P 0.58 / R 1.00.

| System | Field | Precision | Recall | F1 | Exact | TP / FP / FN |
|---|---|---|---|---|---|---|
| LLM (meta-llama/llama-3.3-70b-instruct) | commodities | 1.00 | 0.75 | 0.86 | 0.85 | 9 / 0 / 3 |
| LLM (meta-llama/llama-3.3-70b-instruct) | sourcing_countries | 0.64 | 1.00 | 0.78 | 0.90 | 7 / 4 / 0 |
| LLM (meta-llama/llama-3.3-70b-instruct) | operational_countries | 0.45 | 0.86 | 0.59 | 0.80 | 31 / 38 / 5 |
| Keyword fallback (no LLM) | commodities | 0.86 | 1.00 | 0.92 | 0.90 | 12 / 2 / 0 |
| Keyword fallback (no LLM) | sourcing_countries | 0.06 | 1.00 | 0.11 | 0.45 | 7 / 114 / 0 |
| Keyword fallback (no LLM) | operational_countries | – | 0.00 | – | 0.60 | 0 / 0 / 36 |

The keyword fallback cannot tell sourcing from operations: every country it finds counts as sourcing.

**Sourcing vs operations mix-ups (LLM):** 0 gold sourcing countries were returned as operational
(so they drop out of the risk score), and 0 gold operational countries were returned as sourcing.

## Per company (LLM)

Missed = in the gold labels but not predicted; extra = predicted but not in the gold labels.

| Company | Field | Missed | Extra |
|---|---|---|---|
| Mondelez International | sourcing_countries | – | Côte d'Ivoire |
| Mondelez International | operational_countries | Chile, Colombia, Costa Rica, Paraguay, Uruguay | – |
| Olam | sourcing_countries | – | Côte d'Ivoire, Ghana, Indonesia |
| Olam | operational_countries | – | Argentina, Bolivia, Brazil, Cameroon, Central African Republic, Chile, China, Colombia, Costa Rica, Democratic Republic of Congo, Ecuador, Guatemala, Guyana, Honduras, India, Laos, Liberia, Madagascar, Malaysia, Mexico, Mozambique, Myanmar, Nigeria, Papua New Guinea, Paraguay, Peru, Philippines, Republic of Congo, Sierra Leone, South Africa, Suriname, Tanzania, Thailand, Uruguay, Venezuela, Vietnam |
| IOI Group | commodities | Timber | – |
| Kering | operational_countries | – | China |
| Mondi | commodities | Timber | – |
| Asia Pulp Paper | operational_countries | – | Indonesia |
| Pirelli | commodities | Rubber | – |
