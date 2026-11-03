import os
import datetime
import pandas as pd
import pytest
from src.metrics.kpi_definitions import (
    NET_SENTIMENT_TARGET,
    get_kpi_status,
    get_brand_health_status,
    get_data_quality_status
)
from src.metrics.brand_metrics import calculate_shannon_entropy, calculate_brand_momentum, calculate_brand_metrics
from src.metrics.competitor_metrics import calculate_competitor_metrics, calculate_topic_ownership
from src.metrics.customer_metrics import calculate_customer_experience_metrics, generate_risk_opportunity_scorecard
from src.metrics.operational_metrics import calculate_operational_metrics
from src.metrics.star_schema import generate_star_schema

def test_kpi_definitions_and_status() -> None:
    # Test target threshold categories
    assert get_kpi_status(55.0, NET_SENTIMENT_TARGET) == "Outstanding"  # 55/50 = 1.1
    assert get_kpi_status(46.0, NET_SENTIMENT_TARGET) == "On Target"     # 46/50 = 0.92
    assert get_kpi_status(36.0, NET_SENTIMENT_TARGET) == "Below Target"  # 36/50 = 0.72
    assert get_kpi_status(25.0, NET_SENTIMENT_TARGET) == "Critical"      # 25/50 = 0.50

    assert get_brand_health_status(85.0) == "Excellent"
    assert get_brand_health_status(65.0) == "Good"
    assert get_brand_health_status(45.0) == "Fair"
    assert get_brand_health_status(30.0) == "Critical"

    assert get_data_quality_status(96.0) == "Excellent"


def test_shannon_topic_diversity() -> None:
    # 1. Test empty list
    assert calculate_shannon_entropy([]) == 0.0
    
    # 2. Test single category
    assert calculate_shannon_entropy([10]) == 0.0
    
    # 3. Test equal distributions (should yield max entropy log2(2) = 1.0)
    assert calculate_shannon_entropy([5, 5]) == 1.0
    
    # 4. Test unbalanced distributions
    assert 0.0 < calculate_shannon_entropy([1, 9]) < 1.0


def test_brand_momentum_and_null_safety() -> None:
    # 1. Null safety check
    assert calculate_brand_momentum(pd.DataFrame(), "Mamaearth") == 0.0
    
    # 2. Two periods check
    now = datetime.datetime.utcnow().timestamp()
    data = [
        # Last Month: 1 Positive Review -> Net = 100
        {"brand": "Minimalist", "sentiment_label": "positive", "created_at": now - 86400 * 30},
        # Current Month: 1 Negative Review -> Net = -100
        {"brand": "Minimalist", "sentiment_label": "negative", "created_at": now}
    ]
    df = pd.DataFrame(data)
    # Momentum = -100 - 100 = -200
    assert calculate_brand_momentum(df, "Minimalist") == -200.0


def test_competitor_gaps_sov_ownership() -> None:
    data = [
        {"brand": "Mamaearth", "source": "amazon", "sentiment_label": "positive"},
        {"brand": "Mamaearth", "source": "reddit", "sentiment_label": "negative"},
        {"brand": "Minimalist", "source": "amazon", "sentiment_label": "positive"},
        {"brand": "Minimalist", "source": "amazon", "sentiment_label": "positive"}
    ]
    df = pd.DataFrame(data)
    
    # Mamaearth = 2 docs, Minimalist = 2 docs -> 50% SOV each
    metrics = calculate_competitor_metrics(df, pd.DataFrame())
    assert metrics["mamaearth_sov"] == 50.0
    assert metrics["minimalist_sov"] == 50.0
    
    # Mamaearth net = (1 - 1)/2 = 0
    # Minimalist net = (2 - 0)/2 = 100
    # Gap = 100 - 0 = 100
    assert metrics["sentiment_gap"] == 100.0
    
    # Complaint Gap (Mamaearth 1 neg - Minimalist 0 neg = 1)
    assert metrics["complaint_gap"] == 1
    # Praise Gap (Minimalist 2 pos - Mamaearth 1 pos = 1)
    assert metrics["praise_gap"] == 1


def test_customer_metrics_and_concentration() -> None:
    pos_data = [
        {"mapped_topic": "Effective Ingredients", "brand": "Minimalist"},
        {"mapped_topic": "Effective Ingredients", "brand": "Minimalist"},
        {"mapped_topic": "Visible Results", "brand": "Minimalist"}
    ]
    neg_data = [
        {"mapped_topic": "Hair Fall", "brand": "Mamaearth"},
        {"mapped_topic": "Hair Fall", "brand": "Mamaearth"},
        {"mapped_topic": "Packaging Issues", "brand": "Mamaearth"},
        {"mapped_topic": "Unmapped", "brand": "Mamaearth"}
    ]
    df_pos = pd.DataFrame(pos_data)
    df_neg = pd.DataFrame(neg_data)
    
    cx = calculate_customer_experience_metrics(df_pos, df_neg)
    assert cx["top_praise_category"] == "Effective Ingredients"
    # 2 out of 3 praise documents (100% mapped) -> 2/3 * 100 = 66.67
    assert cx["praise_concentration"] == 66.67
    
    assert cx["top_complaint_category"] == "Hair Fall"
    # Exclude unmapped: 2 out of 3 complaints mapped -> 2/3 * 100 = 66.67
    assert cx["complaint_concentration"] == 66.67

    # Risk scorecard
    ro = generate_risk_opportunity_scorecard(df_pos, df_neg)
    assert len(ro) == 4
    
    # Hair Fall count = 2 -> Medium priority risk
    hf_row = ro[ro["Topic"] == "Hair Fall"].iloc[0]
    assert hf_row["Type"] == "Risk"
    assert hf_row["Priority"] == "Medium"
    
    # Effective Ingredients count = 2 -> Medium priority opportunity
    ing_row = ro[ro["Topic"] == "Effective Ingredients"].iloc[0]
    assert ing_row["Type"] == "Opportunity"
    assert ing_row["Priority"] == "Medium"


def test_operational_completeness_and_runs() -> None:
    data = [
        {"source_record_id": "r1", "source": "amazon", "brand": "Mamaearth", "text": "A", "author": "u1"},
        {"source_record_id": "r2", "source": "amazon", "brand": "Minimalist", "text": None, "author": None} # 3 nulls out of 5 cols
    ]
    df = pd.DataFrame(data)
    
    # Total cells crucial: 10. Non-null: 8. Completeness = 80.0%
    op = calculate_operational_metrics("non_existent_db.db", df)
    assert op["records_processed"] == 2
    assert op["sources_covered"] == 1
    assert op["data_completeness"] == 80.0


def test_star_schema_export_integrity(tmp_path) -> None:
    exports_dir = tmp_path / "exports"
    
    now = datetime.datetime.utcnow().timestamp()
    results_data = [
        {"source_record_id": "r1", "source": "amazon", "brand": "Mamaearth", "title": "T", "text": "B", "rating": 5.0, "author": "u1", "created_at": now, "sentiment_score": 1.0, "sentiment_confidence": 0.95},
        {"source_record_id": "r2", "source": "reddit", "brand": "Minimalist", "title": "A", "text": "C", "rating": None, "author": "u2", "created_at": now, "sentiment_score": -1.0, "sentiment_confidence": 0.90}
    ]
    df_results = pd.DataFrame(results_data)
    
    pos_data = [
        {"source_record_id": "r1", "brand": "Mamaearth", "mapped_topic": "Effective Ingredients", "raw_topic": "ingredients"}
    ]
    neg_data = [
        {"source_record_id": "r2", "brand": "Minimalist", "mapped_topic": "Hair Fall", "raw_topic": "shampoo"}
    ]
    df_pos = pd.DataFrame(pos_data)
    df_neg = pd.DataFrame(neg_data)

    fact, d_brand, d_topic, d_source, d_date = generate_star_schema(
        df_results, df_pos, df_neg, str(exports_dir)
    )

    # Verify files generated
    assert os.path.exists(exports_dir / "fact_customer_feedback.csv")
    assert os.path.exists(exports_dir / "dim_brand.csv")
    assert os.path.exists(exports_dir / "dim_topic.csv")
    assert os.path.exists(exports_dir / "dim_source.csv")
    assert os.path.exists(exports_dir / "dim_date.csv")

    # Verify dimensions sizes
    assert len(d_brand) == 2
    assert len(d_source) == 2
    assert len(d_topic) == 2
    assert len(fact) == 2

    # Verify key integrity constraints
    # Brand keys in fact must match dim_brand keys
    fact_brand_keys = set(fact["brand_key"].tolist())
    dim_brand_keys = set(d_brand["brand_key"].tolist())
    assert fact_brand_keys.issubset(dim_brand_keys)

    # Topic keys in fact must match dim_topic keys
    fact_topic_keys = set(fact["topic_key"].tolist())
    dim_topic_keys = set(d_topic["topic_key"].tolist())
    assert fact_topic_keys.issubset(dim_topic_keys)

    # Source keys in fact must match dim_source keys
    fact_source_keys = set(fact["source_key"].tolist())
    dim_source_keys = set(d_source["source_key"].tolist())
    assert fact_source_keys.issubset(dim_source_keys)

    # Date keys in fact must match dim_date keys
    fact_date_keys = set(fact["date_key"].tolist())
    dim_date_keys = set(d_date["date_key"].tolist())
    assert fact_date_keys.issubset(dim_date_keys)
