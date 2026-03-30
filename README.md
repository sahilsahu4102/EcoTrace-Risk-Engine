# 🌍 EcoTrace-Risk-Engine: AI-Powered Supply Chain Deforestation Scorer

An intelligent, multi-source risk assessment platform that helps consumers and enterprises evaluate corporate supply chains for deforestation risks using deterministic data and LLM-powered extraction.

![Phase](https://img.shields.io/badge/Phase-5%20of%205-purple)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/Frontend-Next.js-black)
![License](https://img.shields.io/badge/License-MIT-blue)

🎥 **[Watch the Full Product Demo Video Here](https://drive.google.com/file/d/1NmSob4oo__kMoqJXP2d5VNSBq-QMZX0c/view?usp=sharing)**

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
Calculates a unified deforestation risk score (0-100) based on intrinsic commodity risk and regional vulnerability. We track 15 key commodities and 40+ high-risk countries.

### LLM-Powered CSR Extraction
Large Language Models read and extract entity data (commodities and sourcing regions) from unstructured Corporate Sustainability (CSR) and ESG pages, turning corporate PR into structured data.

### Transparent Confidence Scoring
Returns a dedicated "Confidence Score" based on the density of corroborating public records, explicitly flagging companies with zero disclosed sourcing information.

### Sub-second Caching Layer
An embedded SQLite caching layer natively stores and serves previously analyzed supply chains, slashing API latency from ~60 seconds to single-digit milliseconds for repeat queries.

### Interactive Next.js Dashboard
A modern, glassmorphism web interface visualizes:
- Overall risk & confidence scores
- Commodity-to-Region risk matrices
- Live Global Forest Watch (GFW) tree cover loss statistics
- A globally shared "Search History" audit log

> **Note on CDP Disclosure Limitations:** 
> Full CDP (Carbon Disclosure Project) supply chain reports are gated behind institutional memberships. Because of this limitation in fetching raw CDP reports openly, EcoTrace utilizes AI-driven scraping of public CSR/ESG pages and deterministic NGO datasets as an effective proxy for formal supply chain disclosures.

## 💡 Key Innovation
Most sustainability trackers rely heavily on manual data entry or isolated datasets. 

EcoTrace introduces a hybrid architecture:
- **Deterministic datasets (Trase, Forest 500, GFW)** guarantee rigorous baseline metrics.
- **LLM extraction** provides real-time parsing of the latest corporate disclosures.

This allows analysts and consumers to make faster, highly-explainable risk assessments.

## 🧠 System Architecture

```text
User Search (Company or Category)
   ↓
API Rate Limiter & Cache Check
   ↓
Parallel Data Orchestration (asyncio)
  ├── Trase Trade Data (CSV)
  ├── Forest 500 Policies (CSV)
  ├── GFW Tree Cover Loss (REST API)
  └── CSR Page Scraper → LLM Extraction
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
- API Keys: Global Forest Watch, Scrapingdog, OpenRouter (Gemini/Llama)

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
- **Phase 1** — Core Risk Engine & Pydantic Data Models
- **Phase 2** — Data Integrations (Trase, Forest 500, GFW)
- **Phase 3** — CSR Scraper & API Endpoint
- **Phase 4** — Next.js Visual Dashboard
- **Phase 5** — Caching, History, Tests & Production Polish

*Detailed phase outlines and scoring methodology are available in the `docs/` directory.*

## 🔮 Future Improvements
EcoTrace operates as a robust prototype, but future roadmap items include:
- **Direct CDP API Integration:** For enterprise users with Institutional CDP credentials to bypass CSR proxy scraping.
- **Geospatial Sub-national Parsing:** Upgrading GFW queries from country-level to geostore boundaries for exact farm/mill risk mapping.
- **Predictive ML Modeling:** Training models on historical deforestation events to proactively predict future supply chain violations.

## 📜 License
This project is released under the MIT License.
