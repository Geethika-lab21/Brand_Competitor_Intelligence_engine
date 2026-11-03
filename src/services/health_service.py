import os
import sqlite3
from functools import lru_cache
import pandas as pd
from typing import Dict, Any

@lru_cache(maxsize=32)
def _read_text_cached(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


@lru_cache(maxsize=32)
def _query_db_cached(db_path: str, query: str) -> pd.DataFrame:
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def clear_health_cache() -> None:
    _read_text_cached.cache_clear()
    _query_db_cached.cache_clear()


def get_pipeline_health(db_path: str = "database/brand_intelligence.db") -> pd.DataFrame:
    """
    Returns pipeline history and run monitoring metrics from SQLite collection_runs.
    """
    query = "SELECT * FROM collection_runs ORDER BY id DESC LIMIT 50;"
    return _query_db_cached(db_path, query).copy()


def get_dataset_summary(db_path: str = "database/brand_intelligence.db") -> Dict[str, int]:
    """
    Counts total records and unique users/subreddits stored in SQLite.
    """
    results = {
        "total_posts": 0,
        "total_comments": 0,
        "unique_authors": 0,
        "unique_subreddits": 0
    }
    
    if not os.path.exists(db_path):
        return results
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Total Posts
        cursor.execute("SELECT COUNT(*) FROM posts;")
        results["total_posts"] = cursor.fetchone()[0]
        
        # 2. Total Comments
        cursor.execute("SELECT COUNT(*) FROM comments;")
        results["total_comments"] = cursor.fetchone()[0]
        
        # 3. Unique Authors (combine posts and comments)
        cursor.execute("""
            SELECT COUNT(DISTINCT author) FROM (
                SELECT author FROM posts WHERE author IS NOT NULL AND author != 'anonymous'
                UNION ALL
                SELECT author FROM comments WHERE author IS NOT NULL AND author != 'anonymous'
            );
        """)
        results["unique_authors"] = cursor.fetchone()[0]
        
        # 4. Unique Subreddits
        cursor.execute("""
            SELECT COUNT(DISTINCT subreddit) FROM (
                SELECT subreddit FROM posts WHERE subreddit IS NOT NULL AND subreddit != ''
                UNION ALL
                SELECT subreddit FROM comments WHERE subreddit IS NOT NULL AND subreddit != ''
            );
        """)
        results["unique_subreddits"] = cursor.fetchone()[0]
        
        conn.close()
    except Exception:
        pass
        
    return results


def get_model_summary(reports_dir: str = "reports") -> Dict[str, Any]:
    """
    Parses sentiment and topic modeling execution diagnostics from generated markdown reports.
    """
    summary = {
        "sentiment_model": "Unknown",
        "sentiment_throughput_sec": 0.0,
        "sentiment_fallback_usage_pct": 0.0,
        "topic_model_positive": "Unknown",
        "topic_model_negative": "Unknown",
        "topics_pos_count": 0,
        "topics_neg_count": 0
    }
    
    # 1. Parse model_performance.md
    perf_path = os.path.join(reports_dir, "model_performance.md")
    perf_content = _read_text_cached(perf_path)
    if perf_content:
        lines = perf_content.split("\n")
        for line in lines:
            stripped = line.strip()
            if "model name" in stripped.lower():
                parts = stripped.split("|")
                if len(parts) >= 3:
                    summary["sentiment_model"] = parts[2].replace("`", "").strip()
            elif "throughput rate" in stripped.lower():
                parts = stripped.split("|")
                if len(parts) >= 3:
                    try:
                        # e.g. "1.23 records/second" -> parse 1.23
                        val_str = parts[2].split()[0]
                        summary["sentiment_throughput_sec"] = float(val_str)
                    except (ValueError, IndexError):
                        pass
            elif "fallback usage percentage" in stripped.lower():
                parts = stripped.split("|")
                if len(parts) >= 3:
                    try:
                        val_str = parts[2].replace("%", "").strip()
                        summary["sentiment_fallback_usage_pct"] = float(val_str)
                    except (ValueError, IndexError):
                        pass

    # 2. Parse topic_model_performance.md
    topic_perf_path = os.path.join(reports_dir, "topic_model_performance.md")
    topic_perf_content = _read_text_cached(topic_perf_path)
    if topic_perf_content:
        lines = topic_perf_content.split("\n")
        for line in lines:
            stripped = line.strip()
            if "model type (positive)" in stripped.lower():
                parts = stripped.split("|")
                if len(parts) >= 3:
                    summary["topic_model_positive"] = parts[2].replace("`", "").strip()
            elif "model type (negative)" in stripped.lower():
                parts = stripped.split("|")
                if len(parts) >= 3:
                    summary["topic_model_negative"] = parts[2].replace("`", "").strip()
            elif "topics discovered (positive)" in stripped.lower():
                parts = stripped.split("|")
                if len(parts) >= 3:
                    try:
                        summary["topics_pos_count"] = int(parts[2].strip())
                    except ValueError:
                        pass
            elif "topics discovered (negative)" in stripped.lower():
                parts = stripped.split("|")
                if len(parts) >= 3:
                    try:
                        summary["topics_neg_count"] = int(parts[2].strip())
                    except ValueError:
                        pass
                        
    return summary
