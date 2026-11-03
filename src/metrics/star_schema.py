import os
import datetime
import pandas as pd
from typing import Dict, Any, Tuple

def generate_star_schema(
    results_df: pd.DataFrame,
    df_pos_annotated: pd.DataFrame,
    df_neg_annotated: pd.DataFrame,
    exports_dir: str
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generates relational Power BI-ready Star Schema tables and saves them as CSV.
    
    Returns:
        Tuple of (fact_feedback, dim_brand, dim_topic, dim_source, dim_date)
    """
    os.makedirs(exports_dir, exist_ok=True)
    
    if results_df.empty:
        # Return empty dataframes matching the structure
        empty_brand = pd.DataFrame(columns=["brand_key", "brand_name"])
        empty_topic = pd.DataFrame(columns=["topic_key", "mapped_topic", "raw_topic"])
        empty_source = pd.DataFrame(columns=["source_key", "source_name"])
        empty_date = pd.DataFrame(columns=["date_key", "full_date", "year", "month", "month_name", "quarter", "day_of_week"])
        empty_fact = pd.DataFrame(columns=["feedback_id", "brand_key", "topic_key", "source_key", "date_key", "sentiment_score", "sentiment_confidence", "rating", "raw_text_length"])
        return empty_fact, empty_brand, empty_topic, empty_source, empty_date

    # 1. Map topics to results_df
    # We combine annotated pos and neg dataframes to build a map of record_id -> (mapped_topic, raw_topic)
    topic_map = {}
    
    if not df_pos_annotated.empty:
        for _, row in df_pos_annotated.iterrows():
            rec_id = str(row["source_record_id"])
            topic_map[rec_id] = (str(row["mapped_topic"]), str(row["raw_topic"]))
            
    if not df_neg_annotated.empty:
        for _, row in df_neg_annotated.iterrows():
            rec_id = str(row["source_record_id"])
            topic_map[rec_id] = (str(row["mapped_topic"]), str(row["raw_topic"]))

    # 2. Build Dimension Tables
    
    # A. dim_brand
    brands = sorted(results_df["brand"].unique())
    brand_rows = [{"brand_key": idx + 1, "brand_name": b} for idx, b in enumerate(brands)]
    dim_brand = pd.DataFrame(brand_rows)
    brand_lookup = {b: idx + 1 for idx, b in enumerate(brands)}
    
    # B. dim_source
    sources = sorted(results_df["source"].unique())
    source_rows = [{"source_key": idx + 1, "source_name": s} for idx, s in enumerate(sources)]
    dim_source = pd.DataFrame(source_rows)
    source_lookup = {s: idx + 1 for idx, s in enumerate(sources)}
    
    # C. dim_topic
    # Build unique topics set
    unique_topics = set()
    for _, row in results_df.iterrows():
        rec_id = str(row["source_record_id"])
        mapped, raw = topic_map.get(rec_id, ("Unmapped", "general feedback"))
        unique_topics.add((mapped, raw))
        
    unique_topics_list = sorted(list(unique_topics))
    topic_rows = [{"topic_key": idx + 1, "mapped_topic": t[0], "raw_topic": t[1]} for idx, t in enumerate(unique_topics_list)]
    dim_topic = pd.DataFrame(topic_rows)
    topic_lookup = {t: idx + 1 for idx, t in enumerate(unique_topics_list)}
    
    # D. dim_date
    date_rows = []
    date_lookup = {}
    
    # Process unique dates based on created_at epoch
    unique_timestamps = results_df["created_at"].dropna().unique()
    for ts in unique_timestamps:
        dt = datetime.datetime.utcfromtimestamp(float(ts))
        date_key = int(dt.strftime("%Y%m%d"))
        
        if date_key not in date_lookup:
            date_lookup[date_key] = date_key
            date_rows.append({
                "date_key": date_key,
                "full_date": dt.date().isoformat(),
                "year": dt.year,
                "month": dt.month,
                "month_name": dt.strftime("%B"),
                "quarter": (dt.month - 1) // 3 + 1,
                "day_of_week": dt.strftime("%A")
            })
            
    # Default date lookup for null timestamps
    default_date_key = 19700101
    if default_date_key not in date_lookup:
        date_rows.append({
            "date_key": default_date_key,
            "full_date": "1970-01-01",
            "year": 1970,
            "month": 1,
            "month_name": "January",
            "quarter": 1,
            "day_of_week": "Thursday"
        })
        
    dim_date = pd.DataFrame(date_rows).sort_values(by="date_key").reset_index(drop=True)

    # 3. Build Fact Table (fact_customer_feedback)
    fact_rows = []
    for _, row in results_df.iterrows():
        rec_id = str(row["source_record_id"])
        
        # Foreign Keys lookups
        brand_name = row["brand"]
        b_key = brand_lookup.get(brand_name, -1)
        
        source_name = row["source"]
        s_key = source_lookup.get(source_name, -1)
        
        mapped, raw = topic_map.get(rec_id, ("Unmapped", "general feedback"))
        t_key = topic_lookup.get((mapped, raw), -1)
        
        # Date key lookup
        ts = row.get("created_at")
        if pd.notnull(ts):
            dt = datetime.datetime.utcfromtimestamp(float(ts))
            d_key = int(dt.strftime("%Y%m%d"))
        else:
            d_key = default_date_key
            
        # Rating & Text stats
        rating_val = float(row["rating"]) if pd.notnull(row.get("rating")) else None
        text_val = str(row.get("text", ""))
        raw_len = len(text_val)
        
        fact_rows.append({
            "feedback_id": rec_id,
            "brand_key": b_key,
            "topic_key": t_key,
            "source_key": s_key,
            "date_key": d_key,
            "sentiment_score": float(row["sentiment_score"]),
            "sentiment_confidence": float(row["sentiment_confidence"]),
            "rating": rating_val,
            "raw_text_length": raw_len
        })
        
    fact_feedback = pd.DataFrame(fact_rows)

    # 4. Save to files
    dim_brand.to_csv(os.path.join(exports_dir, "dim_brand.csv"), index=False, encoding="utf-8")
    dim_topic.to_csv(os.path.join(exports_dir, "dim_topic.csv"), index=False, encoding="utf-8")
    dim_source.to_csv(os.path.join(exports_dir, "dim_source.csv"), index=False, encoding="utf-8")
    dim_date.to_csv(os.path.join(exports_dir, "dim_date.csv"), index=False, encoding="utf-8")
    fact_feedback.to_csv(os.path.join(exports_dir, "fact_customer_feedback.csv"), index=False, encoding="utf-8")
    
    return fact_feedback, dim_brand, dim_topic, dim_source, dim_date
