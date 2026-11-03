import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_shannon_entropy(counts: List[int]) -> float:
    """
    Computes Shannon Entropy to represent Topic Diversity.
    Formula: H = -sum(p_i * log2(p_i))
    """
    total = sum(counts)
    if total == 0:
        return 0.0
    entropy = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            entropy -= p * np.log2(p)
    return round(entropy, 4)


def calculate_brand_momentum(df: pd.DataFrame, brand: str) -> float:
    """
    Computes brand sentiment momentum: Current Month Net Sentiment - Last Month Net Sentiment.
    Returns 0.0 if timeline is single-period or data is missing.
    """
    if df.empty or "created_at" not in df.columns:
        return 0.0
        
    df_brand = df[df["brand"].str.lower() == brand.lower()].copy()
    if len(df_brand) < 2:
        return 0.0
        
    try:
        df_brand["datetime"] = pd.to_datetime(df_brand["created_at"], unit="s")
        df_brand["year_month"] = df_brand["datetime"].dt.to_period("M").astype(str)
        
        monthly_scores = []
        for ym, gp in df_brand.groupby("year_month"):
            tot = len(gp)
            pos = sum(gp["sentiment_label"] == "positive")
            neg = sum(gp["sentiment_label"] == "negative")
            net = ((pos - neg) / tot * 100) if tot > 0 else 0.0
            monthly_scores.append((ym, net))
            
        # Sort chronologically
        monthly_scores.sort(key=lambda x: x[0])
        if len(monthly_scores) >= 2:
            return round(monthly_scores[-1][1] - monthly_scores[-2][1], 2)
    except Exception:
        pass
        
    return 0.0


def calculate_brand_metrics(results_df: pd.DataFrame, df_topics: pd.DataFrame, brand: str) -> Dict[str, Any]:
    """
    Aggregates all BI brand metrics for a given brand.
    """
    metrics = {
        "brand_name": brand,
        "net_sentiment": 0.0,
        "positive_rate": 0.0,
        "negative_rate": 0.0,
        "visibility": 0,
        "topic_diversity": 0.0,
        "momentum": 0.0
    }
    
    if results_df.empty:
        return metrics
        
    df_brand = results_df[results_df["brand"].str.lower() == brand.lower()]
    total = len(df_brand)
    metrics["visibility"] = total
    
    if total > 0:
        pos = sum(df_brand["sentiment_label"] == "positive")
        neg = sum(df_brand["sentiment_label"] == "negative")
        neu = sum(df_brand["sentiment_label"] == "neutral")
        
        metrics["net_sentiment"] = round(((pos - neg) / total * 100), 2)
        metrics["positive_rate"] = round((pos / total * 100), 2)
        metrics["negative_rate"] = round((neg / total * 100), 2)
        
    # Topic diversity (exclude 'Unmapped' to evaluate core thematic breadth)
    if not df_topics.empty:
        brand_topics = df_topics[(df_topics["brand"].str.lower() == brand.lower()) & (df_topics["mapped_topic"] != "Unmapped")]
        if not brand_topics.empty:
            topic_counts = brand_topics.groupby("mapped_topic").size().tolist()
            metrics["topic_diversity"] = calculate_shannon_entropy(topic_counts)
            
    # Trend Momentum
    metrics["momentum"] = calculate_brand_momentum(results_df, brand)
    
    return metrics
