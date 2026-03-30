"""
Forest 500 Data Service for Deforestation Risk Scorer.

Loads Forest 500 company assessment data from CSV,
provides fuzzy company matching, and returns policy scores,
commodity exposure, and assessment details.

Forest 500: https://forest500.org/
"""

import os
from difflib import get_close_matches
from typing import Optional

import pandas as pd


class Forest500Service:
    """Service for querying Forest 500 company rankings."""

    def __init__(self, data_dir: str = "data/forest500"):
        self.data_dir = data_dir
        self._df: Optional[pd.DataFrame] = None
        self._company_names: list[str] = []
        self._loaded = False

    def load(self) -> bool:
        """
        Load Forest 500 CSV data.

        Returns True if data was loaded successfully, False otherwise.
        """
        if self._loaded:
            return True

        csv_path = os.path.abspath(self.data_dir)
        if not os.path.exists(csv_path):
            print(f"[Forest500] Data directory not found: {csv_path}")
            return False

        # Look for CSV files
        csv_files = [
            f for f in os.listdir(csv_path)
            if f.endswith(".csv")
        ]

        if not csv_files:
            print(f"[Forest500] No CSV files found in: {csv_path}")
            return False

        frames = []
        for csv_file in csv_files:
            try:
                filepath = os.path.join(csv_path, csv_file)
                df = pd.read_csv(filepath, low_memory=False, encoding="utf-8")
                df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
                frames.append(df)
                print(f"[Forest500] Loaded: {csv_file} ({len(df)} rows)")
            except Exception as e:
                print(f"[Forest500] Failed to load {csv_file}: {e}")

        if not frames:
            print("[Forest500] No valid CSV data loaded.")
            return False

        self._df = pd.concat(frames, ignore_index=True, sort=False)
        print(f"[Forest500] Total rows: {len(self._df)}")

        # Extract company names
        self._company_names = self._extract_company_names()
        print(f"[Forest500] Unique companies indexed: {len(self._company_names)}")

        self._loaded = True
        return True

    def _extract_company_names(self) -> list[str]:
        """Extract unique company names from DataFrame."""
        if self._df is None:
            return []

        name_columns = [
            "name", "company", "company_name", "organisation",
            "organization", "entity_name", "institution",
        ]

        names = set()
        for col in name_columns:
            if col in self._df.columns:
                col_names = self._df[col].dropna().unique()
                names.update(str(n).strip() for n in col_names if str(n).strip())

        return sorted(names)

    def search(self, company: str, cutoff: float = 0.6) -> dict:
        """
        Search for a company in Forest 500 data using fuzzy matching.

        Args:
            company: Company name to search for
            cutoff: Fuzzy match threshold (0-1)

        Returns:
            Dict with matched company name, policy scores, commodities, and assessment.
        """
        if not self._loaded:
            if not self.load():
                return {
                    "status": "not_available",
                    "error": "Forest 500 data not loaded. See data/README.md for download instructions.",
                }

        # Fuzzy match
        matches = get_close_matches(
            company.lower(),
            [n.lower() for n in self._company_names],
            n=3,
            cutoff=cutoff,
        )

        if not matches:
            return {
                "status": "not_found",
                "company_searched": company,
                "policy_score": None,
                "commodities": [],
            }

        # Map back to original case
        matched_names = []
        for m in matches:
            for orig in self._company_names:
                if orig.lower() == m:
                    matched_names.append(orig)
                    break

        # Filter DataFrame
        name_columns = [
            "name", "company", "company_name", "organisation",
            "organization", "entity_name", "institution",
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
                "policy_score": None,
                "commodities": [],
            }

        # Extract policy/overall score
        policy_score = self._extract_score(filtered)

        # Extract commodity exposure
        commodities = self._extract_commodities(filtered)

        # Extract category scores
        category_scores = self._extract_category_scores(filtered)

        # Extract headquarters/sector info
        metadata = self._extract_metadata(filtered)

        return {
            "status": "found",
            "company_searched": company,
            "matched_names": matched_names,
            "total_records": len(filtered),
            "policy_score": policy_score,
            "commodities": commodities,
            "category_scores": category_scores,
            "metadata": metadata,
        }

    def _extract_score(self, df: pd.DataFrame) -> Optional[float]:
        """Extract the overall/policy score."""
        score_columns = [
            "total_score", "overall_score", "score", "total",
            "policy_score", "total_percentage", "percentage",
        ]
        for col in score_columns:
            if col in df.columns:
                numeric = pd.to_numeric(df[col], errors="coerce")
                valid = numeric.dropna()
                if not valid.empty:
                    return round(float(valid.iloc[0]), 1)
        return None

    def _extract_commodities(self, df: pd.DataFrame) -> list[str]:
        """Extract commodity data from Forest 500."""
        commodity_cols = [
            col for col in df.columns
            if any(kw in col.lower() for kw in [
                "commodity", "palm", "soy", "beef", "cattle",
                "timber", "pulp", "paper", "cocoa", "rubber",
                "coffee",
            ])
        ]

        commodities = set()
        for col in commodity_cols:
            # Check if the column has non-zero/non-null scores
            numeric = pd.to_numeric(df[col], errors="coerce")
            if numeric.sum() > 0:
                # Extract commodity name from column name — ONLY use known keywords
                for keyword in [
                    "palm oil", "soy", "beef", "cattle", "timber",
                    "pulp", "paper", "cocoa", "rubber", "coffee",
                ]:
                    if keyword in col:
                        commodities.add(keyword.title())
                        break
                # If no keyword matched, skip it — do NOT use raw column names

        # Also check for text-based commodity columns
        text_cols = ["commodity", "commodities", "key_commodities"]
        for col in text_cols:
            if col in df.columns:
                vals = df[col].dropna().unique()
                for v in vals:
                    for item in str(v).split(","):
                        clean = item.strip()
                        if clean:
                            commodities.add(clean.title())

        return sorted(commodities)

    def _extract_category_scores(self, df: pd.DataFrame) -> dict:
        """Extract individual category scores from Forest 500."""
        category_keywords = [
            "governance", "commitment", "transparency", "implementation",
            "social", "reporting", "traceability", "monitoring",
        ]

        scores = {}
        for col in df.columns:
            for keyword in category_keywords:
                if keyword in col.lower():
                    numeric = pd.to_numeric(df[col], errors="coerce")
                    valid = numeric.dropna()
                    if not valid.empty:
                        scores[keyword] = round(float(valid.iloc[0]), 1)
                    break

        return scores

    def _extract_metadata(self, df: pd.DataFrame) -> dict:
        """Extract company metadata like headquarters, sector, etc."""
        metadata_cols = {
            "headquarters": ["headquarters", "hq", "country", "hq_country"],
            "sector": ["sector", "industry", "category", "type"],
            "jurisdiction": ["jurisdiction", "jurisdiction_country"],
        }

        result = {}
        for key, possible_cols in metadata_cols.items():
            for col in possible_cols:
                if col in df.columns:
                    val = df[col].dropna()
                    if not val.empty:
                        result[key] = str(val.iloc[0]).strip()
                        break

        return result

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def company_count(self) -> int:
        return len(self._company_names)
