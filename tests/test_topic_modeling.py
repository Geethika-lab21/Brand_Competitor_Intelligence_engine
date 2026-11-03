import os
import pandas as pd
import pytest
from src.topic_modeling.topic_extractor import TopicExtractor
from src.topic_modeling.topic_metrics import (
    calculate_pain_praise_points,
    calculate_topic_gap_analysis,
    calculate_topic_sentiment_matrix
)
from src.topic_modeling.topic_reports import generate_topic_reports

def test_topic_extractor_lexical_fallback() -> None:
    # 1. Initialize extractor forced to lexical fallback
    extractor = TopicExtractor(force_fallback="lexical")
    
    # 2. Build mock dataset
    data = [
        {"title": "Shampoo feedback", "text": "This onion shampoo caused massive hairfall clumps!"},
        {"title": "Pricing feedback", "text": "The products are too expensive and not worth the cost."},
        {"title": "Sunscreen feedback", "text": "Leaves a white cast and makes skin greasy."},
        {"title": "Irrelevant feedback", "text": "The weather is lovely today."}
    ]
    df = pd.DataFrame(data)
    
    # Run negative topic modeling
    df_annotated, diagnostics = extractor.extract_topics(df, is_positive=False)
    
    # Check diagnostics
    assert diagnostics["model_used"] == "Lexical Category Fallback"
    assert diagnostics["records_analyzed"] == 4
    
    # Check annotations
    assert df_annotated.iloc[0]["mapped_topic"] == "Hair Fall"
    assert df_annotated.iloc[1]["mapped_topic"] == "Price Concerns"
    assert df_annotated.iloc[2]["mapped_topic"] == "White Cast"
    assert df_annotated.iloc[3]["mapped_topic"] == "Unmapped"

def test_topic_extractor_nmf_fallback() -> None:
    extractor = TopicExtractor(force_fallback="nmf")
    
    # We need enough documents for NMF modeling (say 16 to exceed minimum of 15 docs)
    # Build 16 mock documents
    data = []
    for i in range(8):
        data.append({"title": "Hair care", "text": "I used the shampoo wash and experienced severe hairfall and hair shedding."})
        data.append({"title": "Active ingredients", "text": "The niacinamide formula salicylic acid clears acne spots."})
    df = pd.DataFrame(data)
    
    df_annotated, diagnostics = extractor.extract_topics(df, is_positive=True, min_docs_for_modeling=10)
    
    assert diagnostics["model_used"] == "NMF Fallback"
    assert diagnostics["topics_discovered"] > 0
    assert "raw_topic" in df_annotated.columns
    assert "mapped_topic" in df_annotated.columns

def test_metrics_gap_and_matrix() -> None:
    # Setup mock annotated dataframes
    pos_data = [
        {"mapped_topic": "Effective Ingredients", "brand": "Minimalist", "sentiment_label": "positive"},
        {"mapped_topic": "Effective Ingredients", "brand": "Minimalist", "sentiment_label": "positive"},
        {"mapped_topic": "Visible Results", "brand": "Minimalist", "sentiment_label": "positive"},
        {"mapped_topic": "Good Packaging", "brand": "Mamaearth", "sentiment_label": "positive"}
    ]
    neg_data = [
        {"mapped_topic": "Hair Fall", "brand": "Mamaearth", "sentiment_label": "negative"},
        {"mapped_topic": "Hair Fall", "brand": "Mamaearth", "sentiment_label": "negative"},
        {"mapped_topic": "Packaging Issues", "brand": "Mamaearth", "sentiment_label": "negative"},
        {"mapped_topic": "Packaging Issues", "brand": "Minimalist", "sentiment_label": "negative"},
        {"mapped_topic": "Unmapped", "brand": "Mamaearth", "sentiment_label": "negative"}
    ]
    df_pos = pd.DataFrame(pos_data)
    df_neg = pd.DataFrame(neg_data)
    
    # 1. Check gap analysis
    gap_df = calculate_topic_gap_analysis(df_pos, df_neg)
    assert not gap_df.empty
    
    # Hair Fall: Mamaearth = 2, Minimalist = 0 -> Gap: +2
    hf_row = gap_df[gap_df["Topic"] == "Hair Fall"].iloc[0]
    assert hf_row["Mamaearth"] == 2
    assert hf_row["Minimalist"] == 0
    assert hf_row["Gap"] == "+2"
    
    # Effective Ingredients: Mamaearth = 0, Minimalist = 2 -> Gap: -2
    ing_row = gap_df[gap_df["Topic"] == "Effective Ingredients"].iloc[0]
    assert ing_row["Mamaearth"] == 0
    assert ing_row["Minimalist"] == 2
    assert ing_row["Gap"] == "-2"

    # 2. Check sentiment matrix
    combined = pd.concat([df_pos, df_neg], ignore_index=True)
    matrix_df = calculate_topic_sentiment_matrix(combined)
    assert not matrix_df.empty
    
    hf_matrix = matrix_df[matrix_df["topic"] == "Hair Fall"].iloc[0]
    assert hf_matrix["negative_count"] == 2
    assert hf_matrix["positive_count"] == 0

def test_reports_and_confidence_scoring(tmp_path) -> None:
    # Build temporary reports directory
    reports_dir = tmp_path / "reports"
    
    # Mock data with confidence scores
    pos_data = [
        {"source_record_id": "p1", "source": "amazon", "title": "Great", "text": "Active niacinamide works.", "mapped_topic": "Effective Ingredients", "raw_topic": "niacinamide, active", "brand": "Minimalist", "sentiment_label": "positive", "sentiment_confidence": 0.95},
        {"source_record_id": "p2", "source": "amazon", "title": "Clears skin", "text": "Salicylic acid cleanses.", "mapped_topic": "Effective Ingredients", "raw_topic": "salicylic, clears", "brand": "Minimalist", "sentiment_label": "positive", "sentiment_confidence": 0.90},
        {"source_record_id": "p3", "source": "amazon", "title": "Good results", "text": "Improvement in 3 weeks.", "mapped_topic": "Visible Results", "raw_topic": "results, weeks", "brand": "Minimalist", "sentiment_label": "positive", "sentiment_confidence": 0.85}
    ]
    neg_data = [
        {"source_record_id": "n1", "source": "amazon", "title": "Hairfall", "text": "Onion shampoo fall.", "mapped_topic": "Hair Fall", "raw_topic": "hairfall, onion", "brand": "Mamaearth", "sentiment_label": "negative", "sentiment_confidence": 0.96},
        {"source_record_id": "n2", "source": "amazon", "title": "Bad cap", "text": "Leaking bottle cap.", "mapped_topic": "Packaging Issues", "raw_topic": "leaking, cap", "brand": "Mamaearth", "sentiment_label": "negative", "sentiment_confidence": 0.94},
        {"source_record_id": "n3", "source": "amazon", "title": "Broken pump", "text": "Pump is broken.", "mapped_topic": "Packaging Issues", "raw_topic": "pump, broken", "brand": "Mamaearth", "sentiment_label": "negative", "sentiment_confidence": 0.92}
    ]
    
    df_pos = pd.DataFrame(pos_data)
    df_neg = pd.DataFrame(neg_data)
    results_df = pd.concat([df_pos, df_neg], ignore_index=True)
    
    diagnostics = {"model_used": "TestModel", "topics_discovered": 2, "processing_time_sec": 0.1}

    generate_topic_reports(
        df_pos_annotated=df_pos,
        df_neg_annotated=df_neg,
        results_df=results_df,
        diagnostics_pos=diagnostics,
        diagnostics_neg=diagnostics,
        reports_dir=str(reports_dir)
    )

    # 1. Check pain and praise point CSVs
    assert os.path.exists(reports_dir / "customer_pain_points.csv")
    assert os.path.exists(reports_dir / "customer_praise_points.csv")
    
    # 2. Check recommendations file containing confidence scores
    recs_file = reports_dir / "recommendations.md"
    assert os.path.exists(recs_file)
    with open(recs_file, "r") as f:
        recs_content = f.read()
    
    # Packaging Issues: count = 2, avg_conf = 0.93 -> Should be 'Medium'
    assert "Topic: Packaging Issues" in recs_content
    assert "Recommendation Confidence**: **Medium**" in recs_content

    # Hair Fall: count = 1, avg_conf = 0.96 -> Should be 'Low' (since count < 2)
    assert "Topic: Hair Fall" in recs_content
    assert "Recommendation Confidence**: **Low**" in recs_content

    # Effective Ingredients: count = 2, avg_conf = 0.925 -> Should be 'Medium'
    assert "Topic: Effective Ingredients Praise" in recs_content
    
    # 3. Check executive brief exists and does not contain technical jargon
    brief_file = reports_dir / "executive_brief.md"
    assert os.path.exists(brief_file)
    with open(brief_file, "r") as f:
        brief_content = f.read()
    
    # Assert non-technical keywords
    assert "Executive Briefing" in brief_content
    assert "Pain Points" in brief_content
    # Jargon exclusions check
    assert "TF-IDF" not in brief_content
    assert "NMF" not in brief_content
    assert "latent" not in brief_content
    assert "embedding" not in brief_content
