# Data Directory

This directory holds the external datasets used by the Deforestation Risk Scorer.
**These files are NOT committed to Git** — download them manually following the steps below.

## Directory Structure (after setup)

```
data/
├── trase/                       # Trase supply chain CSVs
│   ├── BRAZIL_SOY_2.6.0.csv
│   ├── INDONESIA_PALM_OIL_1.2.csv
│   └── ...
├── forest500/                   # Forest 500 assessment CSV
│   └── forest500_companies.csv
├── region_risk_fallback.json    # ✅ Already included (committed)
└── README.md                    # ✅ This file
```

---

## 1. Trase Data Download

**URL**: https://supplychains.trase.earth/data

### Steps:
1. Go to https://supplychains.trase.earth/data
2. Accept the Terms & Conditions
3. Use the **Bulk Download** section
4. Select country + commodity combinations to download

### Priority Downloads (start with these):
| Country | Commodity | Why |
|---------|-----------|-----|
| Brazil | Soy | Largest soy-linked deforestation dataset |
| Brazil | Beef | Amazon cattle ranching flows |
| Indonesia | Palm Oil | SE Asia palm oil supply chains |
| Paraguay | Soy | Chaco deforestation links |
| Argentina | Soy | Gran Chaco conversion |
| Colombia | Beef | Emerging deforestation frontier |
| Côte d'Ivoire | Cocoa | West African cocoa supply chains |
| Ghana | Cocoa | Cocoa-linked forest loss |
| Malaysia | Palm Oil | Borneo/Sarawak palm oil |
| Bolivia | Soy | Expanding soy frontier |

### After Download:
- Place all `.csv` files in the `data/trase/` folder
- The service auto-detects and loads all CSVs on startup

### Key Columns Used:
- `exporter` / `importer` — company names
- `commodity` — product type
- `country_of_production` — sourcing country
- `volume` / `soy_equivalent_tonnes` — trade volumes
- Columns containing "deforestation" — risk indicators

---

## 2. Forest 500 Data Download

**URL**: https://forest500.org/rankings

### Steps:
1. Go to https://forest500.org/rankings/companies
2. Click **"Download Data"** or export the company rankings table
3. Save as CSV

### After Download:
- Place the CSV in `data/forest500/`
- Name it anything (e.g., `forest500_companies.csv`)

### Key Columns Used:
- `name` / `company` — company name for matching
- `total_score` / `score` — overall policy score
- Commodity-specific columns (palm oil, soy, beef, timber, etc.)
- `headquarters` / `sector` — company metadata

---

## 3. Global Forest Watch (GFW)

**No file download needed** — GFW uses a live REST API.

### API Key Setup:
1. Go to https://www.globalforestwatch.org/my-gfw/
2. Create a free account
3. Generate an API key
4. Add to your `.env` file:
   ```
   GFW_API_KEY=your_key_here
   ```

### Fallback:
If no API key is set, the system automatically uses `region_risk_fallback.json` which contains pre-computed risk data for 40+ countries.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Trase download gives HTML | Make sure you accepted T&Cs first |
| CSV encoding errors | Try opening in a text editor and re-saving as UTF-8 |
| Forest 500 columns don't match | Column names are normalized automatically (lowercase, underscores) |
| GFW API returns 403 | Check your API key in `.env` |
| Missing columns in data | The services handle missing columns gracefully — they just skip them |
