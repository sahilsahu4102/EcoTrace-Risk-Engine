# EcoTrace-Risk-Engine Methodology

## Overview
The EcoTrace Risk Engine computes a unified deforestation risk score (0-100) for supply chains by orchestrating data across multiple public domains: trade records (Trase), public policies (Forest 500), and spatial monitoring (Global Forest Watch).

## 1. Commodity Risk Weights
Each commodity is assigned a base risk weight (0.0 to 1.0) derived from global land-use conversion studies (e.g., WRI, Global Canopy, FAO).

* **Palm Oil (0.95):** The primary driver of tropical deforestation in SE Asia (Indonesia/Malaysia).
* **Beef / Cattle (0.92):** The single largest driver of Amazonian and Cerrado deforestation in South America.
* **Soy (0.90):** Driving extensive land conversion in South America, tightly coupled with global animal feed demands.
* **Timber (0.85):** Direct canopy removal via both legal and illegal logging operations globally.
* **Cocoa (0.80):** High impact in West Africa (Côte d'Ivoire, Ghana), heavily encroaching on protected zones.

## 2. Regional Risk Tiers
Countries are grouped into four risk tiers based on historical tree cover loss (GFW) and remaining intact forest landscapes.

* **Critical (0.85 - 1.00):** e.g., Brazil, Indonesia, DRC. Nations with the highest absolute volume of primary forest loss linked directly to commercial agriculture.
* **High (0.70 - 0.84):** e.g., Colombia, Côte d'Ivoire. Countries with rapidly accelerating deforestation fronts or systemic illegal commodity expansion.
* **Moderate (0.50 - 0.69):** e.g., Vietnam, Mexico. Regions where deforestation is present but either stabilizing or driven by secondary commodities.
* **Lower (< 0.50):** e.g., China, Costa Rica. Countries with stabilizing forest cover or where tree loss is primarily driven by forestry rotation rather than permanent land-use change.

## 3. CDP Data Gap
*Note on CDP (Carbon Disclosure Project) Data:*
Full CDP supply chain reports require institutional access and are gated behind corporate memberships. As an open-data platform, EcoTrace currently scrapes publicly available CSR and ESG pages as a proxy for formal CDP disclosures. Future enterprise versions of this tool would ideally authenticate against the CDP API to pull structured Scope 3 forest impact data natively.

## 4. Scoring Algorithm
The core algorithm calculates a weighted risk matrix:
1. `Base Risk` = `Commodity Weight` × `Region Risk Tier`
2. `Overall Score` = Weighted average of highest-risk pathways, scaled 0-100.
3. `Confidence Score` = Increases based on the density of corroborating public records (Trase volume data + Forest500 tracking). 
