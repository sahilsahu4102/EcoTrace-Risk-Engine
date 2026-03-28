# 🌍 Deforestation Risk Scorer

> Aggregates real public data from Trase, Forest 500, Global Forest Watch, and corporate CSR pages to compute deforestation risk scores for supply chains.

![Phase](https://img.shields.io/badge/Phase-2%20of%205-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)
![Status](https://img.shields.io/badge/Status-Data%20Integrations-yellow)

## 🏗️ Current Status

**Phase 1 — Core Extraction & Scoring Engine** ✅
- 15 deforestation-linked commodities with risk weights
- 40+ high-risk countries/regions with ISO codes and risk tiers
- Cross-product risk scoring algorithm
- Confidence scoring engine
- Pydantic data models

**Upcoming Phases:**
- Phase 2: Trase, Forest 500, GFW data integrations
- Phase 3: CSR scraper + `/api/risk` endpoint
- Phase 4: Next.js frontend dashboard
- Phase 5: Deployment & polish

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Setup
```bash
# Clone the repository
git clone <repo-url>
cd Deforest

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env

# Run the server
uvicorn app.main:app --reload
```

### Test
```bash
# Health check
curl http://localhost:8000/health

# API docs
# Open http://localhost:8000/docs
```

## 🏛️ Architecture

```
project/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── models/
│   │   └── schema.py         # Pydantic request/response models
│   ├── services/
│   │   └── extraction.py     # Commodity & region extraction engine
│   └── utils/
│       └── scoring.py        # Risk & confidence scoring
├── data/
│   └── region_risk_fallback.json  # 40+ country risk data
├── docs/                     # Phase-wise documentation
└── requirements.txt
```

## 📊 Data Sources

| Source | Type | Status |
|--------|------|--------|
| Trase | Supply chain trade flows | 🔜 Phase 2 |
| Forest 500 | Corporate policy rankings | 🔜 Phase 2 |
| Global Forest Watch | Tree cover loss API | 🔜 Phase 2 |
| CSR Scraper | Company sustainability pages | 🔜 Phase 3 |

## 📚 Documentation

Detailed documentation is in the [`docs/`](docs/) folder:
- **[Phase 1: Core Engine, Data Dictionary, Architecture & Setup](docs/phase1.md)**
- **[Phase 2: Data Integrations — Trase, Forest 500, GFW](docs/phase2.md)**

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, Pydantic, pandas
- **Frontend**: Next.js, TypeScript, Tailwind CSS, shadcn/ui (Phase 4)
- **Data**: Trase CSV, Forest 500 CSV, GFW REST API
- **Deployment**: Render/Railway + Vercel (Phase 5)

## 📄 License

MIT
