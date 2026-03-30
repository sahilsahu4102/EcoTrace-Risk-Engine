# Phase 4: Frontend Dashboard

## 1. Overview
Phase 4 introduces a premium, dark-themed Next.js frontend with glassmorphic design, animated visualizations, and a responsive layout. The app consists of two pages: a **search page** and a **results dashboard**.

## 2. Tech Stack
- **Next.js 16** with App Router + TypeScript
- **Tailwind CSS** for utility-first styling
- **Framer Motion** for animations
- **Recharts** for bar and radar charts
- **Lucide React** for icons

## 3. Pages

### Search Page (`/`)
- Animated gradient background blobs
- Central search input with glow focus effect
- Quick-action suggestion chips (Unilever, Cargill, JBS, Wilmar, Nestlé, Mondelez)
- Stats bar: "40+ Countries · 15 Commodities · 4 Data Sources"

### Results Dashboard (`/results/[company]`)
- **Score Gauge**: Animated SVG ring showing risk score 0-100 with dynamic color
- **Metric Cards**: Risk Score, Confidence, Commodities count, Regions count
- **Summary Panel**: AI-generated text assessment
- **Bar Chart**: Commodity × Region combined scores (Recharts)
- **Radar Chart**: Regional risk profile visualization
- **Breakdown Table**: Full commodity × region matrix with inline score bars
- **Disclosure Flags**: Warnings about missing data sources
- **Data Sources Panel**: Status of each source (CSR, Trase, Forest 500, GFW)
- **Loading Skeleton**: Shimmer animation while API responds
- **Error Screen**: Graceful error handling with back navigation

## 4. Setup

```bash
cd frontend
npm install
npm run dev   # Starts on http://localhost:3000
```

Add to `.env.local` if backend is on a different host:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Running Both (backend + frontend):
```bash
# Terminal 1: Backend
cd Deforest
venv\Scripts\activate
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd Deforest/frontend
npm run dev
```

## 5. Component Architecture
```
src/
├── app/
│   ├── layout.tsx          # Root layout, Inter font, animated bg
│   ├── page.tsx            # Search page
│   ├── globals.css         # Full design system
│   └── results/
│       └── [company]/
│           └── page.tsx    # Results dashboard
└── lib/
    └── api.ts              # TypeScript API client
```
