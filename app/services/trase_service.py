"""
Trase Data Service for Deforestation Risk Scorer.

Loads Trase supply chain CSV data from the /data/trase/ directory,
provides fuzzy company name matching, and returns commodity flows,
sourcing regions, and deforestation risk indicators.

Trase data: https://supplychains.trase.earth/
"""

import os
import glob
from difflib import get_close_matches
from typing import Optional

import pandas as pd


class TraseService:
    """Service for querying Trase supply chain data."""

    def __init__(self, data_dir: str = "data/trase"):
        self.data_dir = data_dir
        self._df: Optional[pd.DataFrame] = None
        self._company_names: list[str] = []
        self._loaded = False

    def load(self) -> bool:
        """
        Load all Trase CSV files from the data directory into a unified DataFrame.

        Returns True if data was loaded successfully, False otherwise.
        """
        if self._loaded:
            return True

        csv_path = os.path.abspath(self.data_dir)
        if not os.path.exists(csv_path):
            print(f"[Trase] Data directory not found: {csv_path}")
            return False

        csv_files = glob.glob(os.path.join(csv_path, "*.csv"))
        if not csv_files:
            print(f"[Trase] No CSV files found in: {csv_path}")
            return False

        frames = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file, low_memory=False, encoding="utf-8")
                # Normalize column names: lowercase, strip whitespace, replace spaces
                df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
                frames.append(df)
                print(f"[Trase] Loaded: {os.path.basename(csv_file)} ({len(df)} rows)")
            except Exception as e:
                print(f"[Trase] Failed to load {os.path.basename(csv_file)}: {e}")

        if not frames:
            print("[Trase] No valid CSV data loaded.")
            return False

        self._df = pd.concat(frames, ignore_index=True, sort=False)
        print(f"[Trase] Total unified rows: {len(self._df)}")

        # Extract unique company names from likely columns
        self._company_names = self._extract_company_names()
        print(f"[Trase] Unique company names indexed: {len(self._company_names)}")

        self._loaded = True
        return True

    def _extract_company_names(self) -> list[str]:
        """Extract unique company/exporter/importer names from DataFrame."""
        if self._df is None:
            return []

        name_columns = [
            "exporter", "importer", "company", "trader",
            "exporter_name", "importer_name", "company_name",
            "exporter_group", "importer_group",
        ]

        names = set()
        for col in name_columns:
            if col in self._df.columns:
                col_names = self._df[col].dropna().unique()
                names.update(str(n).strip() for n in col_names if str(n).strip())

        return sorted(names)

    def search(self, company: str, cutoff: float = 0.6) -> dict:
        """
        Search for a company in Trase data using fuzzy matching.

        Args:
            company: Company name to search for
            cutoff: Fuzzy match threshold (0-1)

        Returns:
            Dict with matched company info, commodities, regions, and volumes.
        """
        if not self._loaded:
            if not self.load():
                return {
                    "status": "not_available",
                    "error": "Trase data not loaded. See data/README.md for download instructions.",
                }

        # Fuzzy match company name
        matches = get_close_matches(
            company.lower(),
            [n.lower() for n in self._company_names],
            n=5,
            cutoff=cutoff,
        )

        if not matches:
            return {
                "status": "not_found",
                "company_searched": company,
                "commodities": [],
                "regions": [],
            }

        # Map back to original case names
        matched_names = []
        for m in matches:
            for orig in self._company_names:
                if orig.lower() == m:
                    matched_names.append(orig)
                    break

        # Filter DataFrame for matched companies
        name_columns = [
            "exporter", "importer", "company", "trader",
            "exporter_name", "importer_name", "company_name",
            "exporter_group", "importer_group",
        ]

        mask = pd.Series(False, index=self._df.index)
        for col in name_columns:
            if col in self._df.columns:
                mask |= self._df[col].astype(str).str.strip().isin(matched_names)

        filtered = self._df[mask]

        if filtered.empty:
            return {
                "status": "not_found",
                "company_searched": company,
                "commodities": [],
                "regions": [],
            }

        # Extract commodities
        commodities = self._extract_field(filtered, [
            "commodity", "product", "commodity_name",
        ])

        # Extract regions/countries
        regions = self._extract_field(filtered, [
            "country_of_production", "country", "source_country",
            "country_of_destination", "destination_country",
            "municipality", "state", "biome",
        ])

        # Extract volumes if available
        volume_info = self._extract_volumes(filtered)

        # Extract deforestation risk columns if present
        deforestation_data = self._extract_deforestation_indicators(filtered)

        return {
            "status": "found",
            "company_searched": company,
            "matched_names": matched_names,
            "total_records": len(filtered),
            "commodities": commodities,
            "regions": regions,
            "volumes": volume_info,
            "deforestation_indicators": deforestation_data,
        }

    def _extract_field(self, df: pd.DataFrame, columns: list[str]) -> list[str]:
        """Extract unique non-null values from multiple possible columns."""
        values = set()
        for col in columns:
            if col in df.columns:
                col_vals = df[col].dropna().unique()
                values.update(str(v).strip() for v in col_vals if str(v).strip())
        return sorted(values)

    def _extract_volumes(self, df: pd.DataFrame) -> dict:
        """Extract volume/trade data if columns exist."""
        volume_cols = [
            "volume", "fob", "trade_value", "quantity",
            "soy_equivalent_tonnes", "tonnes",
        ]
        result = {}
        for col in volume_cols:
            if col in df.columns:
                numeric = pd.to_numeric(df[col], errors="coerce")
                result[col] = {
                    "total": round(float(numeric.sum()), 2),
                    "mean": round(float(numeric.mean()), 2),
                    "records": int(numeric.count()),
                }
        return result

    def _extract_deforestation_indicators(self, df: pd.DataFrame) -> dict:
        """Extract deforestation-related columns if they exist."""
        deforestation_cols = [
            col for col in df.columns
            if any(kw in col.lower() for kw in [
                "deforestation", "forest", "land_use", "soy_deforestation",
                "territory_deforestation", "biome_deforestation",
            ])
        ]
        result = {}
        for col in deforestation_cols:
            numeric = pd.to_numeric(df[col], errors="coerce")
            if numeric.count() > 0:
                result[col] = {
                    "total": round(float(numeric.sum()), 2),
                    "mean": round(float(numeric.mean()), 2),
                    "max": round(float(numeric.max()), 2),
                    "records": int(numeric.count()),
                }
        return result

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def company_count(self) -> int:
        return len(self._company_names)

    @property
    def record_count(self) -> int:
        return len(self._df) if self._df is not None else 0
