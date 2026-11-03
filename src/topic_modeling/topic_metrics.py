import pandas as pd
from typing import List, Dict, Any

def calculate_pain_praise_points(df_annotated: pd.DataFrame) -> pd.DataFrame:
    """
    Groups annotated reviews by mapped_topic, brand, and source to compute frequencies
    and aggregate representative review samples.
    
    Columns: topic, frequency, brand, source, sample_reviews
    """
    if df_annotated.empty:
        return pd.DataFrame(columns=["topic", "frequency", "brand", "source", "sample_reviews"])

    # Group by mapped_topic, brand, source
    grouped = df_annotated.groupby(["mapped_topic", "brand", "source"])
    
    records = []
    for (topic, brand, source), group in grouped:
        frequency = len(group)
        
        # Get up to 3 sample reviews (title + text)
        samples = []
        for _, row in group.head(3).iterrows():
            title = str(row["title"]) + " " if pd.notnull(row.get("title")) else ""
            body = str(row["text"]) if pd.notnull(row.get("text")) else ""
            samples.append(f"\"{title.strip()}: {body.strip()}\"" if title else f"\"{body.strip()}\"")
            
        sample_reviews = " | ".join(samples)
        
        # We also want to keep track of raw topics matched under this mapped topic
        raw_topics_list = list(group["raw_topic"].dropna().unique())
        raw_topics_str = ", ".join(raw_topics_list[:3])
        
        records.append({
            "topic": topic,
            "raw_topic": raw_topics_str,
            "frequency": frequency,
            "brand": brand,
            "source": source,
            "sample_reviews": sample_reviews
        })
        
    # Sort by frequency descending
    res_df = pd.DataFrame(records)
    if not res_df.empty:
        res_df = res_df.sort_values(by="frequency", ascending=False)
    return res_df


def calculate_topic_gap_analysis(df_pos: pd.DataFrame, df_neg: pd.DataFrame) -> pd.DataFrame:
    """
    Compares topic counts across brands and calculates the topic gap.
    """
    # Combine positive and negative annotated dataframes
    frames = []
    if not df_pos.empty:
        frames.append(df_pos[["mapped_topic", "brand"]])
    if not df_neg.empty:
        frames.append(df_neg[["mapped_topic", "brand"]])
        
    # Find the top 2 brands dynamically based on volume, sorted alphabetically for deterministic gap comparison
    all_brands = []
    for f in frames:
        all_brands.extend(f["brand"].dropna().tolist())
        
    brand_series = pd.Series(all_brands)
    top_brands = brand_series.value_counts().index.tolist()[:2]
    top_brands = sorted(top_brands)
    brand_a = top_brands[0] if len(top_brands) > 0 else "Mamaearth"
    brand_b = top_brands[1] if len(top_brands) > 1 else "Minimalist"
    
    if not frames:
        return pd.DataFrame(columns=["Topic", brand_a, brand_b, "Gap"])
        
    combined = pd.concat(frames, ignore_index=True)
    
    # Filter out 'Unmapped'
    combined = combined[combined["mapped_topic"] != "Unmapped"]
    
    if combined.empty:
        return pd.DataFrame(columns=["Topic", brand_a, brand_b, "Gap"])
        
    # Get all unique topics
    topics = combined["mapped_topic"].unique()
    
    records = []
    for topic in topics:
        sub = combined[combined["mapped_topic"] == topic]
        brand_a_count = sum(sub["brand"].str.lower() == brand_a.lower())
        brand_b_count = sum(sub["brand"].str.lower() == brand_b.lower())
        gap = brand_a_count - brand_b_count
        
        # Format gap with sign
        gap_sign = f"+{gap}" if gap > 0 else f"{gap}"
        
        records.append({
            "Topic": topic,
            brand_a: brand_a_count,
            brand_b: brand_b_count,
            "Gap": gap_sign
        })
        
    return pd.DataFrame(records)


def calculate_topic_sentiment_matrix(df_annotated: pd.DataFrame) -> pd.DataFrame:
    """
    Computes a matrix showing positive, neutral, and negative counts per mapped topic.
    
    Columns: topic, positive_count, neutral_count, negative_count
    """
    if df_annotated.empty:
        return pd.DataFrame(columns=["topic", "positive_count", "neutral_count", "negative_count"])
        
    # Group by mapped_topic and sentiment_label
    grouped = df_annotated.groupby(["mapped_topic", "sentiment_label"]).size().unstack(fill_value=0)
    
    # Ensure all columns exist
    for col in ["positive", "neutral", "negative"]:
        if col not in grouped.columns:
            grouped[col] = 0
            
    grouped = grouped.reset_index()
    grouped = grouped.rename(columns={
        "mapped_topic": "topic",
        "positive": "positive_count",
        "neutral": "neutral_count",
        "negative": "negative_count"
    })
    
    # Sort by total count descending
    grouped["total"] = grouped["positive_count"] + grouped["neutral_count"] + grouped["negative_count"]
    grouped = grouped.sort_values(by="total", ascending=False).drop(columns=["total"])
    
    return grouped
