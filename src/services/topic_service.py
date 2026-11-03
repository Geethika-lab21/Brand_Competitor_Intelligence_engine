import os
from functools import lru_cache
import pandas as pd

@lru_cache(maxsize=32)
def _read_csv_cached(file_path: str) -> pd.DataFrame:
    """
    Private helper that loads CSV files into Pandas DataFrame and caches the result.
    """
    if not os.path.exists(file_path):
        return pd.DataFrame()
    return pd.read_csv(file_path)


def clear_topic_cache() -> None:
    """
    Clears cache for testing.
    """
    _read_csv_cached.cache_clear()


def get_top_complaints(reports_dir: str = "reports") -> pd.DataFrame:
    """
    Reads the customer pain points from reports/customer_pain_points.csv.
    """
    file_path = os.path.join(reports_dir, "customer_pain_points.csv")
    return _read_csv_cached(file_path).copy()


def get_top_praise(reports_dir: str = "reports") -> pd.DataFrame:
    """
    Reads the customer praise points from reports/customer_praise_points.csv.
    """
    file_path = os.path.join(reports_dir, "customer_praise_points.csv")
    return _read_csv_cached(file_path).copy()


def get_topic_distribution(reports_dir: str = "reports") -> pd.DataFrame:
    """
    Combines both pain and praise dataframes into a single distribution dataframe.
    """
    pain = get_top_complaints(reports_dir)
    praise = get_top_praise(reports_dir)
    
    combined = []
    if not pain.empty:
        pain_copy = pain.copy()
        pain_copy["type"] = "Complaint"
        combined.append(pain_copy)
    if not praise.empty:
        praise_copy = praise.copy()
        praise_copy["type"] = "Praise"
        combined.append(praise_copy)
        
    if not combined:
        return pd.DataFrame()
        
    return pd.concat(combined, ignore_index=True)


def get_topic_sentiment_matrix(reports_dir: str = "reports") -> pd.DataFrame:
    """
    Reads the topic sentiment matrix from reports/topic_sentiment_matrix.csv.
    """
    file_path = os.path.join(reports_dir, "topic_sentiment_matrix.csv")
    return _read_csv_cached(file_path).copy()
