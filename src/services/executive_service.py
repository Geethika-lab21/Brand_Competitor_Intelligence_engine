import os
from functools import lru_cache
import pandas as pd
from typing import List

@lru_cache(maxsize=32)
def _read_text_cached(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def clear_executive_cache() -> None:
    _read_text_cached.cache_clear()


def get_executive_summary(reports_dir: str = "reports") -> str:
    """
    Returns the raw content of reports/executive_brief.md.
    """
    file_path = os.path.join(reports_dir, "executive_brief.md")
    return _read_text_cached(file_path)


def get_key_findings(reports_dir: str = "reports") -> List[str]:
    """
    Parses and returns key findings bullet points from reports/executive_brief.md.
    """
    content = get_executive_summary(reports_dir)
    findings = []
    if not content:
        return findings
        
    lines = content.split("\n")
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##") and "key findings" in stripped.lower():
            in_section = True
            continue
        elif in_section and stripped.startswith("##"):
            break
            
        if in_section and stripped.startswith("*"):
            clean_line = stripped.lstrip("*").strip()
            clean_line = clean_line.replace("**", "")
            findings.append(clean_line)
    return findings


def get_recommendations(reports_dir: str = "reports") -> pd.DataFrame:
    """
    Parses reports/recommendations.md and converts it into a structured Pandas DataFrame.
    """
    file_path = os.path.join(reports_dir, "recommendations.md")
    content = _read_text_cached(file_path)
    
    if not content:
        return pd.DataFrame(columns=["topic", "observation", "evidence", "recommendation", "confidence"])
        
    lines = content.split("\n")
    records = []
    current_rec = {}
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Topic:"):
            # If we already have a record, save it
            if current_rec:
                records.append(current_rec)
            topic = stripped.replace("## Topic:", "").strip()
            current_rec = {
                "topic": topic,
                "observation": "",
                "evidence": "",
                "recommendation": "",
                "confidence": ""
            }
        elif current_rec:
            if "observation" in stripped.lower() and ":" in stripped:
                parts = stripped.split(":", 1)
                current_rec["observation"] = parts[1].replace("**", "").strip()
            elif "evidence" in stripped.lower() and ":" in stripped:
                parts = stripped.split(":", 1)
                current_rec["evidence"] = parts[1].replace("**", "").strip()
            elif "recommendation" in stripped.lower() and ":" in stripped:
                # Need to check that we don't accidentally match recommendation confidence here
                if "recommendation confidence" in stripped.lower():
                    parts = stripped.split(":", 1)
                    current_rec["confidence"] = parts[1].replace("**", "").strip()
                else:
                    parts = stripped.split(":", 1)
                    current_rec["recommendation"] = parts[1].replace("**", "").strip()
                    
    if current_rec:
        records.append(current_rec)
        
    return pd.DataFrame(records)
