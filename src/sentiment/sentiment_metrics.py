import pandas as pd
from typing import Dict, Any

def calculate_sentiment_metrics(df: pd.DataFrame, groupby_col: str = "brand") -> pd.DataFrame:
    """
    Aggregates sentiment predictions grouped by a target column (brand or source).
    Calculates positive %, neutral %, negative %, and Net Sentiment Score.
    
    Formula:
        Net Sentiment = ((Positive - Negative) / Total) * 100
        
    Args:
        df (pd.DataFrame): Dataframe containing 'sentiment_label' column.
        groupby_col (str): Target group column name.
        
    Returns:
        pd.DataFrame: Aggregated metrics DataFrame.
    """
    if df.empty or "sentiment_label" not in df.columns:
        return pd.DataFrame()

    grouped = df.groupby(groupby_col)
    rows = []
    
    for name, group in grouped:
        total = len(group)
        if total == 0:
            continue
            
        pos_count = sum(group["sentiment_label"] == "positive")
        neu_count = sum(group["sentiment_label"] == "neutral")
        neg_count = sum(group["sentiment_label"] == "negative")
        
        pos_pct = (pos_count / total) * 100
        neu_pct = (neu_count / total) * 100
        neg_pct = (neg_count / total) * 100
        
        # Calculate Net Sentiment Score
        net_sentiment = ((pos_count - neg_count) / total) * 100
        
        rows.append({
            groupby_col: name,
            "total_records": total,
            "positive_pct": round(pos_pct, 2),
            "neutral_pct": round(neu_pct, 2),
            "negative_pct": round(neg_pct, 2),
            "net_sentiment": round(net_sentiment, 2)
        })
        
    return pd.DataFrame(rows)
