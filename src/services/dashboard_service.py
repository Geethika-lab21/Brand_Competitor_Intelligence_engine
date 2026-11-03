from typing import Dict, Any, List
import pandas as pd
from src.services.sentiment_service import get_sentiment_summary, get_source_sentiment, get_sentiment_trends
from src.services.topic_service import get_top_complaints, get_top_praise, get_topic_distribution, get_topic_sentiment_matrix
from src.services.competitor_service import get_topic_gaps, get_brand_strengths, get_brand_weaknesses, get_competitor_comparison
from src.services.executive_service import get_key_findings, get_recommendations, get_executive_summary

def get_executive_dashboard_data(reports_dir: str = "reports") -> Dict[str, Any]:
    """
    Orchestrates and aggregates executive brief metrics for the main board page.
    """
    findings = get_key_findings(reports_dir)
    recs_df = get_recommendations(reports_dir)
    summary_df = get_sentiment_summary(reports_dir)
    
    # Extract overall brand sentiments
    brand_sentiments = {}
    if not summary_df.empty:
        # Filter out the Gap row
        base_summary = summary_df[~summary_df["brand"].str.contains("Gap", na=False)]
        for _, row in base_summary.iterrows():
            brand_sentiments[row["brand"]] = {
                "total_records": int(row["total_records"]) if pd.notnull(row.get("total_records")) else 0,
                "net_sentiment": float(row["net_sentiment"]) if pd.notnull(row.get("net_sentiment")) else 0.0
            }
            
    return {
        "title": "Executive Briefing Dashboard",
        "key_findings": findings,
        "brand_sentiments": brand_sentiments,
        "recommendations": recs_df.to_dict(orient="records"),
        "raw_brief": get_executive_summary(reports_dir)
    }

def get_sentiment_dashboard_data(reports_dir: str = "reports", data_dir: str = "data") -> Dict[str, Any]:
    """
    Orchestrates and aggregates detailed sentiment trends and platform distributions.
    """
    summary_df = get_sentiment_summary(reports_dir)
    source_df = get_source_sentiment(reports_dir)
    trends_df = get_sentiment_trends(data_dir)
    
    # Calculate Brand Sentiment Gap
    gap_val = 0.0
    if not summary_df.empty:
        gap_row = summary_df[summary_df["brand"].str.contains("Gap", na=False)]
        if not gap_row.empty:
            gap_val = float(gap_row.iloc[0]["net_sentiment"])
            
    return {
        "title": "Brand Sentiment Performance Dashboard",
        "overall_summary": summary_df.to_dict(orient="records"),
        "sentiment_gap": gap_val,
        "source_breakdown": source_df.to_dict(orient="records"),
        "monthly_trends": trends_df.to_dict(orient="records") if not trends_df.empty else []
    }

def get_voc_dashboard_data(reports_dir: str = "reports") -> Dict[str, Any]:
    """
    Orchestrates and aggregates VoC topics, pain points, praise, and sentiment matrices.
    """
    pain_df = get_top_complaints(reports_dir)
    praise_df = get_top_praise(reports_dir)
    dist_df = get_topic_distribution(reports_dir)
    matrix_df = get_topic_sentiment_matrix(reports_dir)
    
    return {
        "title": "Voice of the Customer (VoC) Analysis Dashboard",
        "top_complaints": pain_df.to_dict(orient="records") if not pain_df.empty else [],
        "top_praise": praise_df.to_dict(orient="records") if not praise_df.empty else [],
        "topic_distribution": dist_df.to_dict(orient="records") if not dist_df.empty else [],
        "topic_sentiment_matrix": matrix_df.to_dict(orient="records") if not matrix_df.empty else []
    }

def get_competitor_dashboard_data(reports_dir: str = "reports") -> Dict[str, Any]:
    """
    Orchestrates and aggregates competitor intelligence comparison data.
    """
    gaps_df = get_topic_gaps(reports_dir)
    strengths = get_brand_strengths(reports_dir)
    weaknesses = get_brand_weaknesses(reports_dir)
    comp_brief = get_competitor_comparison(reports_dir)
    
    return {
        "title": "Competitor Intelligence & Gap Analysis Dashboard",
        "topic_gaps": gaps_df.to_dict(orient="records") if not gaps_df.empty else [],
        "brand_strengths": strengths,
        "brand_weaknesses": weaknesses,
        "comparison_report": comp_brief
    }
