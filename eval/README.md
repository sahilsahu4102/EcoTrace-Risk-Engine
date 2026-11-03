# Extraction eval set

`extraction_gold.jsonl` holds one company per line, used by `scripts/eval_extraction.py` to score
`app/services/extraction.py`.

> **The labels are agent-drafted and need human review.** An AI agent read each text and wrote the expected
> fields; nobody has checked them yet. Until someone does, treat every score computed from this file as
> provisional. Set `label_status` to `reviewed` on a line once a person has checked it.

## Fields

- `company`, `url`: the query and the page the scraper settled on.
- `fetched`: the date the text was fetched.
- `text`: an excerpt of the page text `CSRScraper.scrape()` returned (direct HTTP path, first relevant candidate
  page): a 120-character window around every commodity keyword or country name, labelled or not, joined with
  " … ". Unlabelled mentions are kept on purpose; they are the decoys the extractor has to ignore. Production
  passes `extract_entities()` the whole page (up to 10,000 characters), so excerpt scores run lower where the
  page context matters; see `docs/extraction_eval.md`.
- `expected`: `commodities`, `sourcing_countries`, `operational_countries`, using only names from the allowed
  lists in `extraction.py` (`COMMODITIES`, `REGIONS`), since the extractor can output nothing else.
- `label_status`: `agent_draft` or `reviewed`.
- `label_note`: why a borderline call went the way it did.

## Labelling rules

The same rules the extractor's prompt states:

- A commodity counts only when the text says the company sources, buys, produces or uses it in its supply
  chain, not when it is mentioned in passing.
- A country is a **sourcing** country when the text ties it to procuring raw materials (source, buy, farm,
  plantation, smallholder, supply-chain origin), and an **operational** country when it is about offices,
  factories, sales or staff. Unclear mentions go to operational, as the prompt instructs.
- Only what the text states explicitly. Outside knowledge about the company does not count.

## Note on the page text

The excerpts are short quotations from public company web pages (about a fifth of each page), kept so the eval
reproduces after the pages change; `url` points to the full source. The text belongs to the respective
companies.
