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
Calculates a unified deforestation risk score (0-100) based on intrinsic commodity risk and regional vulnerability. We track 15 key commodities and 40+ high-risk countries. Users can input product categories (e.g., palm oil, soy), and the system maps them to high-risk supply chains using Trase and GFW datasets.

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
2.  **Regional Risk Tiers (0.0-1.0):** Countries are grouped into four risk tiers (Critical, High, Moderate, Lower) driven by real-time Global Forest Watch tree-cover loss statistics. (e.g., Brazil and Indonesia = 0.95 Critical).
3.  **Pathway Evaluation:** For every detected supply chain vector, the engine calculates:
    > `Pathway Score = Commodity Base Weight × Regional Risk Tier × 100`
4.  **Final Aggregation:** The final Risk Score is not a simple average. It uses a weighted calculation that pulls the company's total score heavily toward their highest-risk pathway to prevent "greenwashing" by masking high-risk sourcing with low-risk materials. A bonus reduction is applied if the entity has a strong Forest 500 policy.

**What is the Confidence Score?**
A company might look "Low Risk" (score = 15) simply because they hide all their supply chain data. The **Confidence Score (0-100)** measures the transparency of the result. It increases drastically when Trase provides exact trade volumes, Forest 500 confirms monitoring, or the LLM successfully extracts commodities explicitly admitted on the CSR ESG pages.

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
