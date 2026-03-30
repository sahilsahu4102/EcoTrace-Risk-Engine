# The EcoTrace Paradigm: Re-engineering Deforestation Risk

*A letter to the evaluators detailing the architecture, design choices, and philosophy behind EcoTrace-Risk-Engine.*

## The Core Problem: The Supply Chain Black Box

When a consumer—or a B2B buyer—purchases a product containing soy, beef, or palm oil, the exact origin of that commodity is almost never printed on the label. The modern global supply chain is an intentionally opaque web designed to optimize for cost, not traceability.

A brand (e.g., Nestlé, Unilever) buys from a distributor, who buys from a massive global trader (e.g., Cargill, Bunge), who buys from a regional consolidator, who buys from thousands of individual farms or mills. If a farm in the Brazilian Amazon or Indonesian Borneo clears primary rainforest illegally, by the time that soy or palm kernel oil reaches the brand level, its "dirty" origin is completely mixed with "clean" commodities. 

Currently, evaluating a brand's deforestation risk requires researchers to manually:
1. Dig through vague, 100-page Corporate Sustainability (CSR/ESG) PDF reports.
2. Cross-reference stated sourcing regions against satellite imagery of tree cover loss.
3. Check if the company has a strong "zero-deforestation" policy (and if they actually enforce it).

This manual process is slow, subjective, and unscalable. Our goal with EcoTrace was to **automate this exact investigative journalism workflow** using modern data orchestration and AI.

## The EcoTrace Approach: Hybrid Intelligence

Most "AI" sustainability tools fall into a trap: they ask an LLM (like ChatGPT) to *guess* a company's deforestation risk. LLMs hallucinate numbers, invent policies, and cannot access real-time trade volume data. 

To solve this, EcoTrace uses a **Hybrid Architecture**: deterministic datasets for the math, and LLMs strictly for the language extraction.

### 1. Deterministic Ground Truth (The Math)
We anchor our risk scoring entirely on hard, verifiable, objective data:
* **Trase Earth (2.5GB local data):** We process massive CSV exports of actual customs and port trade data, mapping the exact volume of commodities flowing from specific producing countries to specific importing companies.
* **Forest 500 (Global Canopy):** We integrate the definitive NGO rankings of corporate policies. If a company claims zero-deforestation but Forest 500 rates their actual execution a 1/5, our engine strictly honors the NGO's assessment.
* **Global Forest Watch (GFW API):** The ultimate arbiter. We dynamically query the University of Maryland's satellite tree cover loss API to measure the actual hectares of forest destroyed in a company's sourcing region over the last 5 years.

*If we don't have hard data linking a company to a region, the algorithm refuses to invent a risk score. Instead, it flags the company for "Data Opacity."*

### 2. LLM Information Extraction (The Reader)
Since companies hide their sourcing data in unstructured PR paragraphs on their websites ("We proudly source our cocoa from cooperatives in Côte d'Ivoire..."), deterministic scrapers fail. 

We deployed an advanced Web Scraper (Scrapingdog) to pull raw HTML from corporate domains, and we pipe that text into an instruction-tuned LLM (Meta Llama 3.3 70B via OpenRouter). The LLM's **only job** is to act as a reading comprehension engine: it extracts JSON entities `{"commodity": "Cocoa", "region": "CIV"}` from the PR spin. It is strictly forbidden from generating scores.

## Engineering for Scale and Speed

A major challenge was processing time. Calling an LLM, rendering a headless browser scraper, searching 2.5GB of CSVs with Pandas, and querying a live satellite API takes **upwards of 60 seconds** per search. This is unacceptable for a web dashboard.

**We solved this through three architectural decisions:**
1. **Asynchronous Orchestration:** By using FastAPI's `asyncio.gather()`, we fire all data fetching simultaneously rather than sequentially.
2. **First-Hit Caching Strategy:** We built an embedded SQLite database (`cache_db.py`). The very first time someone searches "Unilever", they wait 45 seconds for a deep extraction. But the result is aggressively cached for 24 hours. The next person who searches "Unilever", or views the Global History tab, receives the deep analysis in **< 50 milliseconds**.
3. **Category Bypasses:** If a user searches for the sheer baseline physics of "Palm Oil" instead of a company name, the engine detects the entity and instantly bypasses the expensive CSR scraper, serving immediate aggregate GFW risk data.

## Why We Built This

EcoTrace fundamentally challenges corporate data opacity. By orchestrating public trade data alongside AI-driven transparency parsing, we strip away corporate "greenwashing" to reveal the underlying physics of supply chain risks. 

It is designed to be unapologetic, entirely data-driven, and lightning-fast. The logic is open, the equations are documented, and the user interface treats the investigator with respect. We believe this represents the future of environmental accountability software.
