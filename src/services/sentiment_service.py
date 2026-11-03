import os
import sqlite3
from functools import lru_cache
import pandas as pd
from typing import Optional

# 1. Caching Helpers
@lru_cache(maxsize=32)
def _read_csv_cached(file_path: str) -> pd.DataFrame:
    """
    Private helper that loads CSV files into Pandas DataFrame and caches the result.
    """
    if not os.path.exists(file_path):
        return pd.DataFrame()
    return pd.read_csv(file_path)


@lru_cache(maxsize=32)
def _query_db_cached(db_path: str, query: str) -> pd.DataFrame:
    """
    Private helper that queries SQLite database and caches the result.
    """
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def clear_sentiment_cache() -> None:
    """
    Clears cache for testing or data updates.
    """
    _read_csv_cached.cache_clear()
    _query_db_cached.cache_clear()


# 2. Public Service Functions (return copies to prevent cache pollution)

def get_sentiment_summary(reports_dir: str = "reports") -> pd.DataFrame:
    """
    Reads the brand sentiment summary metrics with the Brand Sentiment Gap row.
    """
    file_path = os.path.join(reports_dir, "sentiment_summary.csv")
    return _read_csv_cached(file_path).copy()


def get_brand_sentiment(data_dir: str = "data") -> pd.DataFrame:
    """
    Aggregates sentiment count metrics grouped by brand.
    """
    file_path = os.path.join(data_dir, "sentiment_results.csv")
    df = _read_csv_cached(file_path)
    if df.empty:
        return pd.DataFrame()
        
    # Group and aggregate counts
    grouped = df.groupby(["brand", "sentiment_label"]).size().unstack(fill_value=0)
    for col in ["positive", "neutral", "negative"]:
        if col not in grouped.columns:
            grouped[col] = 0
            
    grouped = grouped.reset_index()
    grouped["total_records"] = grouped["positive"] + grouped["neutral"] + grouped["negative"]
    
    # Compute Net Sentiment Score
    grouped["net_sentiment"] = ((grouped["positive"] - grouped["negative"]) / grouped["total_records"] * 100).round(2)
    return grouped


def get_source_sentiment(reports_dir: str = "reports") -> pd.DataFrame:
    """
    Reads the source breakdown metrics (records per source and brand).
    """
    file_path = os.path.join(reports_dir, "source_breakdown.csv")
    return _read_csv_cached(file_path).copy()


def get_sentiment_trends(data_dir: str = "data") -> pd.DataFrame:
    """
    Groups detailed sentiment predictions by year-month and brand to output timeline trends.
    """
    file_path = os.path.join(data_dir, "sentiment_results.csv")
    df = _read_csv_cached(file_path)
    if df.empty or "created_at" not in df.columns:
        return pd.DataFrame()
        
    df_time = df.copy()
    # Handle created_at timestamp
    df_time["datetime"] = pd.to_datetime(df_time["created_at"], unit="s")
    df_time["year_month"] = df_time["datetime"].dt.to_period("M").astype(str)
    
    monthly_net = []
    grouped_time = df_time.groupby(["year_month", "brand"])
    for (ym, brand), gp in grouped_time:
        tot = len(gp)
        pos = sum(gp["sentiment_label"] == "positive")
        neg = sum(gp["sentiment_label"] == "negative")
        net = ((pos - neg) / tot * 100) if tot > 0 else 0.0
        
        monthly_net.append({
            "year_month": ym,
            "brand": brand,
            "net_sentiment": round(net, 2),
            "total_records": tot
        })
        
    return pd.DataFrame(monthly_net)
