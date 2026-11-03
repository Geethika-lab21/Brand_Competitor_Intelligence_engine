import os
from functools import lru_cache
import pandas as pd
from typing import Dict, List

@lru_cache(maxsize=32)
def _read_csv_cached(file_path: str) -> pd.DataFrame:
    if not os.path.exists(file_path):
        return pd.DataFrame()
    return pd.read_csv(file_path)


@lru_cache(maxsize=32)
def _read_text_cached(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def clear_competitor_cache() -> None:
    _read_csv_cached.cache_clear()
    _read_text_cached.cache_clear()


def get_competitor_comparison(reports_dir: str = "reports") -> str:
    """
    Returns the raw content of reports/competitor_intelligence.md.
    """
    file_path = os.path.join(reports_dir, "competitor_intelligence.md")
    return _read_text_cached(file_path)


def get_topic_gaps(reports_dir: str = "reports") -> pd.DataFrame:
    """
    Reads the topic gap analysis CSV.
    """
    file_path = os.path.join(reports_dir, "topic_gap_analysis.csv")
    return _read_csv_cached(file_path).copy()


def _parse_bullet_points(content: str, header: str) -> Dict[str, List[str]]:
    """
    Helper to parse brand strengths/weaknesses from Markdown text under a target header.
    """
    results = {"Mamaearth": [], "Minimalist": []}
    if not content:
        return results
        
    lines = content.split("\n")
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##") and header.lower() in stripped.lower():
            in_section = True
            continue
        elif in_section and stripped.startswith("##"):
            break
            
        if in_section and stripped.startswith("*"):
            # E.g. "* **Minimalist**: Text description..."
            clean_line = stripped.lstrip("*").strip()
            if "minimalist" in clean_line.lower():
                parts = clean_line.split(":", 1)
                text = parts[1].strip() if len(parts) > 1 else clean_line
                # Clean up any trailing/leading markdown bold stars
                text = text.replace("**", "")
                results["Minimalist"].append(text)
            elif "mamaearth" in clean_line.lower():
                parts = clean_line.split(":", 1)
                text = parts[1].strip() if len(parts) > 1 else clean_line
                text = text.replace("**", "")
                results["Mamaearth"].append(text)
    return results


def get_brand_strengths(reports_dir: str = "reports") -> Dict[str, List[str]]:
    """
    Parses and returns brand strengths from reports/executive_brief.md.
    """
    file_path = os.path.join(reports_dir, "executive_brief.md")
    content = _read_text_cached(file_path)
    return _parse_bullet_points(content, "Competitor Strengths")


def get_brand_weaknesses(reports_dir: str = "reports") -> Dict[str, List[str]]:
    """
    Parses and returns brand weaknesses from reports/executive_brief.md.
    """
    file_path = os.path.join(reports_dir, "executive_brief.md")
    content = _read_text_cached(file_path)
    return _parse_bullet_points(content, "Competitor Weaknesses")
