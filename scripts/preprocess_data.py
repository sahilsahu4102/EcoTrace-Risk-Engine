"""
Pre-process Trase and Forest500 CSV data into compact JSON lookup files.

Run this LOCALLY (where you have the raw CSVs) to generate small JSON files
that can be committed to Git and deployed to Render without the huge CSVs.

Uses fast pandas groupby operations instead of per-company iteration.

Usage:
    python scripts/preprocess_data.py

Outputs:
    data/trase_preprocessed.json      (~2-5 MB vs ~2.4 GB raw CSVs)
    data/forest500_preprocessed.json  (~200 KB vs ~25 MB raw CSV)
"""

import os
import sys
import json
import glob
import time

import pandas as pd


# ─── TRASE ─────────────────────────────────────────────────────

def preprocess_trase(data_dir: str = "data/trase") -> dict:
    """
    Read all Trase CSVs and pre-compute per-company lookup data using groupby.
    """
    csv_path = os.path.abspath(data_dir)
    if not os.path.exists(csv_path):
        print(f"[Trase] Data directory not found: {csv_path}")
        return {}

    csv_files = glob.glob(os.path.join(csv_path, "*.csv"))
    if not csv_files:
        print(f"[Trase] No CSV files found in: {csv_path}")
        return {}

    # Identify which name/commodity/region/volume columns exist across files
    name_columns = [
        "exporter", "importer", "company", "trader",
        "exporter_name", "importer_name", "company_name",
        "exporter_group", "importer_group",
    ]
    commodity_columns = ["commodity", "product", "commodity_name", "product_type"]
    region_columns = ["country_of_production", "country", "source_country"]
    volume_columns = ["volume", "fob", "trade_value", "quantity", "soy_equivalent_tonnes", "tonnes"]

    companies: dict[str, dict] = {}  # lowercase name -> aggregated data

    for csv_file in csv_files:
        t0 = time.time()
        basename = os.path.basename(csv_file)
        print(f"\n[Trase] Processing: {basename}...")

        try:
            df = pd.read_csv(csv_file, low_memory=False, encoding="utf-8")
        except Exception as e:
            print(f"[Trase] Failed to load {basename}: {e}")
            continue

        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")

        present_name_cols = [c for c in name_columns if c in df.columns]
        present_commodity_cols = [c for c in commodity_columns if c in df.columns]
        present_region_cols = [c for c in region_columns if c in df.columns]
        present_volume_cols = [c for c in volume_columns if c in df.columns]
        deforestation_cols = [
            col for col in df.columns
            if any(kw in col.lower() for kw in [
                "deforestation", "forest_loss", "land_use_change",
                "soy_deforestation", "territory_deforestation", "biome_deforestation",
            ])
        ]

        if not present_name_cols:
            print(f"  WARN: No name columns found, skipping.")
            continue

        # Process each name column — "melt" so every row is (company_name, row_data)
        for name_col in present_name_cols:
            # Drop rows where this name column is null
            valid = df[df[name_col].notna()].copy()
            if valid.empty:
                continue

            valid["_company_key"] = valid[name_col].astype(str).str.strip()
            valid["_company_lower"] = valid["_company_key"].str.lower()

            # Group by lowercase company name
            grouped = valid.groupby("_company_lower", sort=False)

            for lower_name, group in grouped:
                if not lower_name or lower_name == "nan":
                    continue

                original_name = group["_company_key"].iloc[0]

                if lower_name not in companies:
                    companies[lower_name] = {
                        "names": set(),
                        "commodities": set(),
                        "regions": set(),
                        "total_records": 0,
                        "volumes": {},
                        "deforestation_indicators": {},
                    }

                entry = companies[lower_name]
                entry["names"].add(original_name)
                entry["total_records"] += len(group)

                # Commodities
                for col in present_commodity_cols:
                    vals = group[col].dropna().unique()
                    entry["commodities"].update(str(v).strip() for v in vals if str(v).strip())

                # Regions
                for col in present_region_cols:
                    vals = group[col].dropna().unique()
                    entry["regions"].update(str(v).strip() for v in vals if str(v).strip())

                # Volumes
                for col in present_volume_cols:
                    numeric = pd.to_numeric(group[col], errors="coerce")
                    count = int(numeric.count())
                    if count > 0:
                        total = round(float(numeric.sum()), 2)
                        mean = round(float(numeric.mean()), 2)
                        if col in entry["volumes"]:
                            entry["volumes"][col]["total"] = round(entry["volumes"][col]["total"] + total, 2)
                            entry["volumes"][col]["records"] += count
                        else:
                            entry["volumes"][col] = {"total": total, "mean": mean, "records": count}

                # Deforestation indicators
                for col in deforestation_cols:
                    numeric = pd.to_numeric(group[col], errors="coerce")
                    count = int(numeric.count())
                    if count > 0:
                        total = round(float(numeric.sum()), 2)
                        mean = round(float(numeric.mean()), 2)
                        max_val = round(float(numeric.max()), 2)
                        if col in entry["deforestation_indicators"]:
                            entry["deforestation_indicators"][col]["total"] = round(
                                entry["deforestation_indicators"][col]["total"] + total, 2)
                            entry["deforestation_indicators"][col]["max"] = max(
                                entry["deforestation_indicators"][col]["max"], max_val)
                            entry["deforestation_indicators"][col]["records"] += count
                        else:
                            entry["deforestation_indicators"][col] = {
                                "total": total, "mean": mean, "max": max_val, "records": count,
                            }

        elapsed = time.time() - t0
        print(f"  Done in {elapsed:.1f}s. Running total: {len(companies)} companies")

    if not companies:
        return {}

    # Convert sets to sorted lists for JSON serialization
    all_names = set()
    for key, entry in companies.items():
        entry["names"] = sorted(entry["names"])
        entry["commodities"] = sorted(entry["commodities"])
        entry["regions"] = sorted(entry["regions"])
        all_names.update(entry["names"])
        # Recalculate mean for merged volumes
        for vc in entry["volumes"]:
            v = entry["volumes"][vc]
            if v["records"] > 0:
                v["mean"] = round(v["total"] / v["records"], 2)
        for dc in entry["deforestation_indicators"]:
            d = entry["deforestation_indicators"][dc]
            if d["records"] > 0:
                d["mean"] = round(d["total"] / d["records"], 2)

    result = {
        "company_names": sorted(all_names),
        "companies": companies,
    }

    print(f"\n[Trase] OK: Pre-processed {len(companies)} unique companies from {len(all_names)} name variants")
    return result


# ─── FOREST 500 ────────────────────────────────────────────────

def preprocess_forest500(data_dir: str = "data/forest500") -> dict:
    """
    Read Forest 500 CSV and pre-compute per-company lookup data.
    Forest500 is small (~25 MB) so simple iteration is fine.
    """
    csv_path = os.path.abspath(data_dir)
    if not os.path.exists(csv_path):
        print(f"[Forest500] Data directory not found: {csv_path}")
        return {}

    csv_files = [f for f in os.listdir(csv_path) if f.endswith(".csv")]
    if not csv_files:
        print(f"[Forest500] No CSV files found in: {csv_path}")
        return {}

    frames = []
    for csv_file in csv_files:
        try:
            filepath = os.path.join(csv_path, csv_file)
            df = pd.read_csv(filepath, low_memory=False, encoding="utf-8")
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            frames.append(df)
            print(f"[Forest500] Loaded: {csv_file} ({len(df)} rows)")
        except Exception as e:
            print(f"[Forest500] Failed: {csv_file}: {e}")

    if not frames:
        return {}

    full_df = pd.concat(frames, ignore_index=True, sort=False)
    print(f"[Forest500] Total rows: {len(full_df)}")
    print(f"[Forest500] Columns: {list(full_df.columns)}")

    # Name columns
    f500_name_cols = [c for c in ["name", "company", "company_name", "organisation", "organization", "entity_name", "institution"] if c in full_df.columns]

    # Score columns
    score_columns = ["total_score", "overall_score", "score", "total", "policy_score", "total_percentage", "percentage"]
    # Category keywords
    category_keywords = ["governance", "commitment", "transparency", "implementation", "social", "reporting", "traceability", "monitoring"]
    # Commodity keywords
    commodity_keywords = ["palm oil", "soy", "beef", "cattle", "timber", "pulp", "paper", "cocoa", "rubber", "coffee"]
    # Metadata columns
    metadata_map = {
        "headquarters": ["headquarters", "hq", "country", "hq_country"],
        "sector": ["sector", "industry", "category", "type"],
        "jurisdiction": ["jurisdiction", "jurisdiction_country"],
    }

    all_names = set()
    for col in f500_name_cols:
        vals = full_df[col].dropna().unique()
        all_names.update(str(n).strip() for n in vals if str(n).strip())

    print(f"[Forest500] Unique companies: {len(all_names)}")

    companies = {}
    for name in sorted(all_names):
        mask = pd.Series(False, index=full_df.index)
        for col in f500_name_cols:
            mask |= full_df[col].astype(str).str.strip() == name

        filtered = full_df[mask]
        if filtered.empty:
            continue

        # Policy score
        policy_score = None
        for col in score_columns:
            if col in filtered.columns:
                numeric = pd.to_numeric(filtered[col], errors="coerce").dropna()
                if not numeric.empty:
                    policy_score = round(float(numeric.iloc[0]), 1)
                    break

        # Commodities
        commodities = set()
        commodity_cols = [
            col for col in filtered.columns
            if any(kw in col.lower() for kw in commodity_keywords)
        ]
        for col in commodity_cols:
            numeric = pd.to_numeric(filtered[col], errors="coerce")
            if numeric.sum() > 0:
                for keyword in commodity_keywords:
                    if keyword in col:
                        commodities.add(keyword.title())
                        break

        text_cols = [c for c in ["commodity", "commodities", "key_commodities"] if c in filtered.columns]
        for col in text_cols:
            vals = filtered[col].dropna().unique()
            for v in vals:
                for item in str(v).split(","):
                    clean = item.strip()
                    if clean:
                        commodities.add(clean.title())

        # Category scores
        cat_scores = {}
        for col in filtered.columns:
            for keyword in category_keywords:
                if keyword in col.lower():
                    numeric = pd.to_numeric(filtered[col], errors="coerce").dropna()
                    if not numeric.empty:
                        cat_scores[keyword] = round(float(numeric.iloc[0]), 1)
                    break

        # Metadata
        metadata = {}
        for key, possible_cols in metadata_map.items():
            for col in possible_cols:
                if col in filtered.columns:
                    val = filtered[col].dropna()
                    if not val.empty:
                        metadata[key] = str(val.iloc[0]).strip()
                        break

        key = name.lower()
        companies[key] = {
            "names": [name],
            "policy_score": policy_score,
            "commodities": sorted(commodities),
            "category_scores": cat_scores,
            "metadata": metadata,
            "total_records": len(filtered),
        }

    result = {
        "company_names": sorted(all_names),
        "companies": companies,
    }

    print(f"[Forest500] OK: Pre-processed {len(companies)} companies")
    return result


# ─── MAIN ──────────────────────────────────────────────────────

def main():
    t_start = time.time()
    print("=" * 60)
    print("[Preprocessor] Starting data pre-processing...")
    print("=" * 60)

    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)

    # Forest 500 (fast, do first)
    print("\n" + "=" * 60)
    print("[1/2] Forest 500")
    print("=" * 60)
    f500_data = preprocess_forest500()
    if f500_data:
        out_path = os.path.join(output_dir, "forest500_preprocessed.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(f500_data, f, ensure_ascii=False)
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"\n[Forest500] Saved to {out_path} ({size_mb:.2f} MB)")
    else:
        print("\n[Forest500] FAIL: No data to process")

    # Trase (large)
    print("\n" + "=" * 60)
    print("[2/2] Trase")
    print("=" * 60)
    trase_data = preprocess_trase()
    if trase_data:
        out_path = os.path.join(output_dir, "trase_preprocessed.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(trase_data, f, ensure_ascii=False)
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"\n[Trase] Saved to {out_path} ({size_mb:.2f} MB)")
    else:
        print("\n[Trase] FAIL: No data to process")

    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"[Preprocessor] Done in {elapsed/60:.1f} minutes!")
    print("  Next steps:")
    print("  1. git add data/trase_preprocessed.json data/forest500_preprocessed.json")
    print("  2. git commit -m 'Add preprocessed data files'")
    print("  3. git push -> deploy to Render")
    print("=" * 60)


if __name__ == "__main__":
    main()
