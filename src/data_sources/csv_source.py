import os
import time
import pandas as pd
from typing import List, Dict, Any, Optional
from src.data_sources.base_source import BaseSource
from src.utils.logger import logger

class CSVSource(BaseSource):
    """
    CSV Data Source implementing the BaseSource interface.
    Loads and reformats any review or discussion CSV dataset (Amazon, Nykaa, Kaggle)
    into the standardized Brand Intelligence schema using fuzzy column mapping.
    """

    def __init__(self, default_source_name: str = "csv_file") -> None:
        """
        Initializes the CSV Source.
        
        Args:
            default_source_name (str): The default platform label if none is detected in file path.
        """
        self.default_source_name = default_source_name
        
        # Fuzzy column name candidates for schema mapping
        self.column_candidates = {
            "source_record_id": ["id", "review_id", "record_id", "uuid", "index", "asin"],
            "title": ["title", "headline", "review_title", "subject", "summary"],
            "text": ["text", "body", "review_body", "content", "review_text", "comment"],
            "rating": ["rating", "score", "stars", "star_rating", "rating_value", "review_rating"],
            "author": ["author", "user", "username", "reviewer_name", "reviewer", "profile_name"],
            "created_at": ["created_at", "timestamp", "date", "created_utc", "time", "review_date"]
        }

    def _resolve_column(self, df: pd.DataFrame, target_key: str, custom_mapping: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Helper to map a target schema key to a column name present in the DataFrame.
        """
        # 1. Check custom mapping first
        if custom_mapping and target_key in custom_mapping:
            col = custom_mapping[target_key]
            if col in df.columns:
                return col
                
        # 2. Check candidates
        candidates = self.column_candidates.get(target_key, [])
        for c in candidates:
            # Case-insensitive check
            for col in df.columns:
                if col.lower() == c.lower():
                    return col
        return None

    def fetch_data(self, brand_name: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Reads reviews from a CSV file, filters by brand (if brand column is present),
        and maps fields to the standardized schema.
        
        Args:
            brand_name (str): Target brand (e.g., 'Mamaearth', 'Minimalist').
            **kwargs:
                csv_path (str): Required. Path to the CSV file.
                source_name (str): Optional. Platform label (e.g. 'amazon', 'nykaa').
                column_mapping (Dict[str, str]): Optional. Custom field mapping.
                
        Returns:
            List[Dict[str, Any]]: Standardized records.
        """
        csv_path = kwargs.get("csv_path", "")
        if not csv_path:
            logger.warning("No 'csv_path' provided to CSVSource. Returning empty list.")
            return []

        if not os.path.exists(csv_path):
            logger.warning(f"CSV path does not exist: {csv_path}. Skipping.")
            return []

        source_name = kwargs.get("source_name", "")
        if not source_name:
            # Infer source name from file name base (e.g. 'amazon_reviews.csv' -> 'amazon')
            base = os.path.basename(csv_path).lower()
            for s in ["amazon", "nykaa", "kaggle", "reddit"]:
                if s in base:
                    source_name = s
                    break
            if not source_name:
                source_name = self.default_source_name

        logger.info(f"CSVSource loading dataset: '{csv_path}' for source '{source_name}'...")
        try:
            df = pd.read_csv(csv_path)
            if df.empty:
                return []

            # Resolve column mapping
            mapping = {}
            custom_map = kwargs.get("column_mapping", {})
            for key in self.column_candidates.keys():
                mapping[key] = self._resolve_column(df, key, custom_map)

            # Resolve brand filtering
            # If the CSV has a 'brand' or 'brand_name' column, filter rows.
            # Otherwise, assume all rows in the file belong to this brand.
            brand_col = next((c for c in df.columns if c.lower() in ["brand", "brand_name"]), None)
            if brand_col:
                brand_df = df[df[brand_col].astype(str).str.lower() == brand_name.lower()]
                logger.info(f"Filtered CSV by brand '{brand_name}' using column '{brand_col}': {len(brand_df)} matching rows.")
            else:
                brand_df = df
                logger.info(f"No brand column found in CSV. Assigning all {len(df)} rows to '{brand_name}'.")

            standardized_records = []
            for idx, row in brand_df.iterrows():
                # 1. Extract record ID
                rec_id_col = mapping["source_record_id"]
                rec_id = str(row[rec_id_col]) if rec_id_col else f"{source_name}_{brand_name.lower()}_{idx}"

                # 2. Extract text (body)
                text_col = mapping["text"]
                text_val = str(row[text_col]) if text_col and pd.notnull(row[text_col]) else ""
                
                if not text_val.strip():
                    continue  # Skip records with no text content

                # 3. Extract title
                title_col = mapping["title"]
                title_val = str(row[title_col]) if title_col and pd.notnull(row[title_col]) else None

                # 4. Extract rating
                rating_col = mapping["rating"]
                try:
                    rating_val = float(row[rating_col]) if rating_col and pd.notnull(row[rating_col]) else None
                except ValueError:
                    rating_val = None

                # 5. Extract author
                author_col = mapping["author"]
                author_val = str(row[author_col]) if author_col and pd.notnull(row[author_col]) else "anonymous"

                # 6. Extract creation time
                # Attempt to parse date or convert to epoch
                time_col = mapping["created_utc"] if mapping["created_at"] is None else mapping["created_at"]
                epoch_time = time.time()
                if time_col and pd.notnull(row[time_col]):
                    val = row[time_col]
                    try:
                        if isinstance(val, (int, float)):
                            epoch_time = float(val)
                        else:
                            # Parse string date
                            epoch_time = pd.to_datetime(val).timestamp()
                    except Exception:
                        pass

                # Assemble record
                standardized_records.append({
                    "source": source_name,
                    "source_record_id": rec_id,
                    "brand": brand_name,
                    "title": title_val,
                    "text": text_val,
                    "rating": rating_val,
                    "author": author_val,
                    "created_at": epoch_time,
                    "metadata": {
                        "original_columns": {str(k): str(v) for k, v in row.to_dict().items() if pd.notnull(v)}
                    }
                })

            logger.info(f"CSVSource ingested {len(standardized_records)} records for brand '{brand_name}' from '{csv_path}'.")
            return standardized_records

        except Exception as e:
            logger.error(f"Error reading/parsing CSV data source: {e}", exc_info=True)
            return []
