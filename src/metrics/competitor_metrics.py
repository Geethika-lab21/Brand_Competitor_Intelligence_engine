import pandas as pd
from typing import Dict, Any, List

def calculate_competitor_metrics(results_df: pd.DataFrame, df_topics: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes overall competitor gaps and SOV benchmarks dynamically.
    """
    # Detect top 2 brands dynamically, sorted alphabetically for deterministic gap comparison
    top_brands = results_df["brand"].value_counts().index.tolist()[:2] if not results_df.empty else []
    top_brands = sorted(top_brands)
    brand_a = top_brands[0] if len(top_brands) > 0 else "Mamaearth"
    brand_b = top_brands[1] if len(top_brands) > 1 else "Minimalist"
    
    benchmarks = {
        "brand_a": brand_a,
        "brand_b": brand_b,
        "brand_a_sov": 0.0,
        "brand_b_sov": 0.0,
        "sentiment_gap": 0.0,
        "complaint_gap": 0,
        "praise_gap": 0
    }
    
    if results_df.empty:
        return benchmarks
        
    total_records = len(results_df)
    a_df = results_df[results_df["brand"].str.lower() == brand_a.lower()]
    b_df = results_df[results_df["brand"].str.lower() == brand_b.lower()]
    
    a_count = len(a_df)
    b_count = len(b_df)
    
    # 1. Share of Voice
    if total_records > 0:
        benchmarks["brand_a_sov"] = round((a_count / total_records * 100), 2)
        benchmarks["brand_b_sov"] = round((b_count / total_records * 100), 2)
        
    # 2. Sentiment Gap (Brand B - Brand A)
    a_net = 0.0
    if a_count > 0:
        a_pos = sum(a_df["sentiment_label"] == "positive")
        a_neg = sum(a_df["sentiment_label"] == "negative")
        a_net = ((a_pos - a_neg) / a_count) * 100
        
    b_net = 0.0
    if b_count > 0:
        b_pos = sum(b_df["sentiment_label"] == "positive")
        b_neg = sum(b_df["sentiment_label"] == "negative")
        b_net = ((b_pos - b_neg) / b_count) * 100
        
    benchmarks["sentiment_gap"] = round(b_net - a_net, 2)
    
    # 3. Complaint Gap (Brand A Neg - Brand B Neg)
    a_neg_cnt = sum(results_df[(results_df["brand"].str.lower() == brand_a.lower())]["sentiment_label"] == "negative")
    b_neg_cnt = sum(results_df[(results_df["brand"].str.lower() == brand_b.lower())]["sentiment_label"] == "negative")
    benchmarks["complaint_gap"] = a_neg_cnt - b_neg_cnt
    
    # 4. Praise Gap (Brand B Pos - Brand A Pos)
    a_pos_cnt = sum(results_df[(results_df["brand"].str.lower() == brand_a.lower())]["sentiment_label"] == "positive")
    b_pos_cnt = sum(results_df[(results_df["brand"].str.lower() == brand_b.lower())]["sentiment_label"] == "positive")
    benchmarks["praise_gap"] = b_pos_cnt - a_pos_cnt
    
    # Backward compatibility keys for tests:
    benchmarks[f"{brand_a.lower()}_sov"] = benchmarks["brand_a_sov"]
    benchmarks[f"{brand_b.lower()}_sov"] = benchmarks["brand_b_sov"]
    
    return benchmarks


def calculate_topic_ownership(df_topics: pd.DataFrame, brand_a: str = "Mamaearth", brand_b: str = "Minimalist") -> pd.DataFrame:
    """
    Determines topic ownership based on which brand has higher mentions per topic.
    """
    if df_topics.empty:
        return pd.DataFrame(columns=["Topic", f"{brand_a} Mentions", f"{brand_b} Mentions", "Owner Brand", "Owner Share %"])
        
    # Filter out unmapped
    df_valid = df_topics[df_topics["mapped_topic"] != "Unmapped"]
    if df_valid.empty:
        return pd.DataFrame(columns=["Topic", f"{brand_a} Mentions", f"{brand_b} Mentions", "Owner Brand", "Owner Share %"])
        
    grouped = df_valid.groupby(["mapped_topic", "brand"]).size().unstack(fill_value=0)
    
    # Ensure both columns exist
    for brand in [brand_a, brand_b]:
        if brand not in grouped.columns:
            grouped[brand] = 0
            
    records = []
    for topic, row in grouped.iterrows():
        a_val = int(row[brand_a])
        b_val = int(row[brand_b])
        total = a_val + b_val
        
        if total == 0:
            owner = "Tie"
            share = 0.0
        elif a_val > b_val:
            owner = brand_a
            share = round((a_val / total * 100), 2)
        elif b_val > a_val:
            owner = brand_b
            share = round((b_val / total * 100), 2)
        else:
            owner = "Tie"
            share = 50.0
            
        records.append({
            "Topic": topic,
            f"{brand_a} Mentions": a_val,
            f"{brand_b} Mentions": b_val,
            "Owner Brand": owner,
            "Owner Share %": share
        })
        
    return pd.DataFrame(records)
