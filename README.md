# 🌍 EcoTrace-Risk-Engine: AI-Powered Supply Chain Deforestation Scorer

An intelligent, multi-source risk assessment platform that helps consumers and enterprises evaluate corporate supply chains for deforestation risks using deterministic data and LLM-powered extraction.

![Phase](https://img.shields.io/badge/Phase-5%20of%205-purple)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/Frontend-Next.js-black)
![License](https://img.shields.io/badge/License-MIT-blue)

🎥 **[Watch the Full Product Demo Video Here](https://drive.google.com/file/d/1NmSob4oo__kMoqJXP2d5VNSBq-QMZX0c/view?usp=sharing)** · 🌐 **[Live demo](https://eco-trace-risk-engine.vercel.app)** (the API runs on Render's free tier, which sleeps when idle: a first request after a quiet spell can take a minute)

---

## 🌲 Why EcoTrace Matters
Every year, millions of hectares of primary forest are cleared for agricultural commodities like soy, palm oil, and beef. 

Consumer goods companies source these commodities from high-risk regions, but connecting a brand to a specific sourcing region requires piecing together supply chain disclosures that are scattered, opaque, and inconsistently formatted.

EcoTrace introduces an AI-assisted risk scoring system that:
- **uncovers hidden supply chain links**
- **holds corporations accountable**
- **provides a unified baseline of deforestation risk**
- **helps users understand exactly *where* and *how* companies source materials**

By combining deterministic trade data (Trase) and public policies (Forest 500) with LLM-powered extraction from corporate disclosures, EcoTrace delivers both accuracy and transparency.

## 🚀 Core Features

### Multi-Source Risk Engine
Calculates a unified deforestation risk score (0-100) based on intrinsic commodity risk and regional vulnerability. We track 15 key commodities and 40+ high-risk countries. Users can input product categories (e.g., palm oil, soy), and the system maps them to high-risk supply chains using Trase and GFW datasets.

### LLM-Powered CSR Extraction
Large Language Models read and extract entity data (commodities and sourcing regions) from unstructured Corporate Sustainability (CSR) and ESG pages, turning corporate PR into structured data.

### Transparent Confidence Scoring
Returns a dedicated "Confidence Score" based on the density of corroborating public records, explicitly flagging companies with zero disclosed sourcing information.

### Sub-second Caching Layer
An embedded SQLite caching layer stores and serves previously analyzed supply chains. Repeat queries return in 3.2 ms (median, n = 25) against 52–174 s for an uncached query (median 103 s, n = 5) before the November 2026 scraper fix; see [docs/cache_benchmark.md](docs/cache_benchmark.md). After it, the eight home-page examples took 3–36 s uncached on a laptop (companies 17–36 s, commodity categories 3–11 s). Results older than a day are still returned at once and recomputed in the background, and the examples ship pre-computed, because the free host's disk resets on every restart.

### Interactive Next.js Dashboard
A modern, glassmorphism web interface visualizes:
- Overall risk & confidence scores
- Commodity-to-Region risk matrices
- Live Global Forest Watch (GFW) tree cover loss statistics
- A globally shared "Search History" audit log

### ⚠️ Why EcoTrace Uses AI Instead of CDP Data
The **Carbon Disclosure Project (CDP)** is the global gold standard for corporate environmental reporting. Ideally, risk engines should just read CDP data. However, there is a major data roadblock:
1. Detailed supply chain data submitted to the CDP is completely locked behind expensive institutional corporate memberships.
2. The general public and open-source models cannot freely access these structured Excel/CSV reports.

**The EcoTrace Solution:** To bypass this paywall, EcoTrace acts as a smart proxy scanner. Instead of relying on private CDP databases, it uses an AI (LLM) to read and comprehend the company's freely available Corporate Sustainability Reports (CSR) and ESG webpages. It extracts the exact same commodity and country links that the company would typically submit to the CDP, democratizing access to supply chain risk data.

## 💡 Key Innovation
Most sustainability trackers rely heavily on manual data entry or isolated datasets. 

EcoTrace introduces a hybrid architecture:
- **Deterministic datasets (Trase, Forest 500, GFW)** guarantee rigorous baseline metrics.
- **LLM extraction** provides real-time parsing of the latest corporate disclosures.

This allows analysts and consumers to make faster, highly-explainable risk assessments.

## 🧮 Score Breakdown Matrix

The **Overall Risk Score (0-100)** is calculated deterministically using a matrix approach:

1.  **Commodity Base Weights (0.0-1.0):** Every commodity is assigned a static risk value. For example, *Palm Oil (0.95)* and *Beef (0.92)* rank highest due to massive historical land conversion, while *Coffee (0.65)* ranks lower.
2.  **Regional Risk Tiers (0.0-1.0):** Countries are grouped into four expert risk tiers (Critical, High, Moderate, Lower), e.g. Brazil 0.95 and Indonesia 0.93. Live Global Forest Watch data moves a country's value by up to ±0.1: the mean tree cover loss of the last three years against the country's own 2011-2020 mean.
3.  **Pathway Evaluation:** For every commodity-country pair the evidence supports, the engine calculates:
    > `Pathway Score = Commodity Base Weight × Regional Risk × 100`

    A pair is supported when Trase records that commodity leaving that country for the company, or when the country is a known producer of the commodity. Other combinations of the commodities and countries found (such as palm oil × Chile) are not scored.
4.  **Final Aggregation:** The Risk Score is the average of the pathway scores. Forest 500 policy scores then adjust it: +5 for a score of 20 or below, +2 up to 60, -10 from 80.

**What is the Confidence Score?**
A company might look "Low Risk" (score = 15) simply because they hide all their supply chain data. The **Confidence Score (0-100)** measures the transparency of the result. It increases drastically when Trase provides exact trade volumes, Forest 500 confirms monitoring, or the LLM successfully extracts commodities explicitly admitted on the CSR ESG pages.

## 🔧 November 2026 data fixes

Using the live demo the way a visitor would turned up six problems, each fixed and covered by tests (103 in total):

| Problem | Fix |
|---|---|
| Every commodity was scored against every country found, so results showed "Palm Oil × Chile" | Only pairs backed by a Trase trade record or a known producer country are scored |
| Trase countries included destination countries (Bolivia's file names the importer in `country`), and cocoa entities had no commodity | `scripts/preprocess_data.py` now takes the country from `country_of_production` and the commodity from the dataset's file name, and keeps per-entity (commodity, country, tonnes) pairs |
| Company search kept only the 5 closest Trase names, dropping most of a group's subsidiaries (Cargill's Côte d'Ivoire cocoa entities) | Every entity whose name contains the query as whole words is matched, accent-insensitive |
| GFW never returned live data: the raster dataset refuses country queries without a geometry, and the error was swallowed | GFW's per-country summary tables (`gadm__tcl__iso_change`, `gadm__integrated_alerts__iso_daily_alerts`) |
| The CSR source tried 44 URLs one by one through a Scrapingdog plan with no requests left: about 37 s, always "not found" | Up to 6 likely URLs concurrently, direct first and then the Jina Reader, within 25 s |
| LLM extraction called a paid model on an account without credits, so it always fell back to keywords | Free OpenRouter models are tried in turn after a 402, 404 or 429 |

## 🧠 System Architecture

```text
User Search (Company or Category)
   ↓
API Rate Limiter & Cache Check (a cached result returns at once; one older than a day is refreshed in the background)
   ↓
Parallel Data Orchestration (asyncio)
  ├── Trase trade records (8 country-commodity datasets, preprocessed JSON)
  ├── Forest 500 policy scores (preprocessed JSON)
  ├── GFW Data API: tree cover loss per country + deforestation alerts in natural forest (last 90 days)
  └── CSR page (direct HTTP, then Jina Reader) → LLM extraction (OpenRouter, free-model fallback chain)
   ↓
Commodity-country pairs supported by the evidence
   ↓
Risk & Confidence Scoring Engine
   ↓
FastAPI Backend (Payload Generation)
   ↓
Next.js Visual Dashboard
```

## 📂 Project Structure

```text
ecotrace/
├─ frontend/                # Next.js 15 App Router Frontend
│   ├─ src/app/
│   │   ├─ history/         # Global search history view
│   │   └─ results/         # Dynamic risk visualizations
│
├─ app/                     # FastAPI Backend
│   ├─ routes/              # API endpoints (risk, history)
│   ├─ services/            # Core integrators (gfw, trase, scraper)
│   ├─ utils/               # Scoring & math logic
│   └─ main.py              # App entry & rate limiting
│
├─ data/                    # Local Datasets & Fallbacks
│   ├─ trase/               # 2.5GB real trade records
│   └─ forest500/           # Corporate masterfiles
│
├─ tests/                   # Pytest suite for core engine
├─ docs/                    # Phase documentation & Methodology
└─ README.md
```

## 🛠️ Setup Instructions

### 1️⃣ Prerequisites
- Python 3.10+
- Node.js 18+
- API keys: Global Forest Watch (free) and OpenRouter (free models work; `OPENROUTER_MODEL` can name a paid one, tried first). Company pages are read through the keyless Jina Reader.

### 2️⃣ Backend Setup
Navigate to the root directory and install dependencies:
```bash
pip install -r requirements.txt
```

Create environment variables:
```bash
cp .env.example .env
```
Fill in your API keys in the `.env` file.

Run the FastAPI server:
```bash
python -m uvicorn app.main:app --reload --port 8000
```
*API docs available at `http://localhost:8000/docs`*

### 3️⃣ Frontend Setup
Navigate to the frontend directory:
```bash
cd frontend
npm install
```

Start the Next.js dev server:
```bash
npm run dev
```
*Dashboard available at `http://localhost:3000`*

## 📖 Phase-by-Phase Development

The project was built systematically to ensure data integrity:
- **Phase 1** — Core Extraction and Scoring Engine
- **Phase 2** — Trase, Forest 500, and GFW Data Services
- **Phase 3** — CSR Scraper and Risk API Endpoint
- **Phase 4** — Frontend Dashboard
- **Phase 5** — Containerization with Docker and Deployment
- **Phase 6** — Product Categorization and Final Bug Fixes

*Detailed phase outlines and scoring methodology are available in the `docs/` directory.*

## 🔮 Future Improvements
EcoTrace operates as a robust prototype, but future roadmap items include:
- **Direct CDP API Integration:** For enterprise users with Institutional CDP credentials to bypass CSR proxy scraping.
- **Geospatial Sub-national Parsing:** Upgrading GFW queries from country-level to geostore boundaries for exact farm/mill risk mapping.
- **Predictive ML Modeling:** Training models on historical deforestation events to proactively predict future supply chain violations.

## 📜 License
This project is released under the MIT License.
