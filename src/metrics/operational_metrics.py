import os
import sqlite3
import datetime
import pandas as pd
from typing import Dict, Any

def calculate_operational_metrics(db_path: str, results_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes system operational status and pipeline health metrics.
    """
    metrics = {
        "records_processed": 0,
        "sources_covered": 0,
        "data_completeness": 100.0,
        "last_refresh_date": datetime.datetime.utcnow().isoformat() + "Z",
        "pipeline_health": 100.0
    }
    
    # 1. Records Processed
    metrics["records_processed"] = len(results_df)
    
    # 2. Sources Covered
    if not results_df.empty and "source" in results_df.columns:
        metrics["sources_covered"] = int(results_df["source"].nunique())
        
    # 3. Data Completeness (percent of non-null values across crucial columns)
    if not results_df.empty:
        crucial_cols = ["source_record_id", "source", "brand", "text", "author"]
        available_cols = [c for c in crucial_cols if c in results_df.columns]
        if available_cols:
            # Calculate non-null ratio
            completeness = results_df[available_cols].notnull().mean().mean() * 100
            metrics["data_completeness"] = round(completeness, 2)
            
    # 4. Pipeline Health (success runs percentage)
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM collection_runs;")
            runs = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            if runs:
                success_count = sum(1 for r in runs if r == "SUCCESS")
                metrics["pipeline_health"] = round((success_count / len(runs) * 100), 2)
        except Exception:
            pass
            
    return metrics
