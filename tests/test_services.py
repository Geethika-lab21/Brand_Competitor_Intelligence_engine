import os
import pandas as pd
import pytest
from src.services.models import SentimentSummary, TopicGap, Recommendation, DashboardData
from src.services.sentiment_service import (
    get_sentiment_summary,
    get_brand_sentiment,
    get_source_sentiment,
    get_sentiment_trends,
    _read_csv_cached,
    clear_sentiment_cache
)
from src.services.topic_service import (
    get_top_complaints,
    get_top_praise,
    get_topic_distribution,
    get_topic_sentiment_matrix
)
from src.services.competitor_service import (
    get_competitor_comparison,
    get_topic_gaps,
    get_brand_strengths,
    get_brand_weaknesses
)
from src.services.executive_service import (
    get_executive_summary,
    get_key_findings,
    get_recommendations
)
from src.services.dashboard_service import (
    get_executive_dashboard_data,
    get_sentiment_dashboard_data,
    get_voc_dashboard_data,
    get_competitor_dashboard_data
)
from src.services.health_service import (
    get_pipeline_health,
    get_dataset_summary,
    get_model_summary
)
from src.utils.database_helper import DatabaseHelper

@pytest.fixture
def mock_reports_dir(tmp_path):
    reports_dir = tmp_path / "reports"
    data_dir = tmp_path / "data"
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    # 1. sentiment_summary.csv
    summary_data = [
        {"brand": "Mamaearth", "total_records": 10, "positive_pct": 60.0, "neutral_pct": 20.0, "negative_pct": 20.0, "net_sentiment": 40.0},
        {"brand": "Minimalist", "total_records": 20, "positive_pct": 80.0, "neutral_pct": 10.0, "negative_pct": 10.0, "net_sentiment": 70.0},
        {"brand": "Brand Sentiment Gap (Minimalist - Mamaearth)", "total_records": None, "positive_pct": None, "neutral_pct": None, "negative_pct": None, "net_sentiment": 30.0}
    ]
    pd.DataFrame(summary_data).to_csv(reports_dir / "sentiment_summary.csv", index=False)
    
    # 2. source_breakdown.csv
    source_data = [
        {"source": "amazon", "brand": "Mamaearth", "records_count": 6},
        {"source": "reddit", "brand": "Mamaearth", "records_count": 4},
        {"source": "amazon", "brand": "Minimalist", "records_count": 20}
    ]
    pd.DataFrame(source_data).to_csv(reports_dir / "source_breakdown.csv", index=False)
    
    # 3. sentiment_results.csv (detailed)
    results_data = [
        {"source": "amazon", "source_record_id": "r1", "brand": "Mamaearth", "title": "A", "text": "B", "rating": 5, "author": "u1", "created_at": 1778562942, "sentiment_label": "positive", "sentiment_score": 1.0, "sentiment_confidence": 0.95},
        {"source": "amazon", "source_record_id": "r2", "brand": "Mamaearth", "title": "C", "text": "D", "rating": 1, "author": "u2", "created_at": 1778562942, "sentiment_label": "negative", "sentiment_score": -1.0, "sentiment_confidence": 0.90},
        {"source": "amazon", "source_record_id": "r3", "brand": "Minimalist", "title": "E", "text": "F", "rating": 5, "author": "u3", "created_at": 1778994942, "sentiment_label": "positive", "sentiment_score": 1.0, "sentiment_confidence": 0.99}
    ]
    pd.DataFrame(results_data).to_csv(data_dir / "sentiment_results.csv", index=False)
    
    # 4. customer_pain_points.csv
    pain_data = [
        {"topic": "Hair Fall", "frequency": 2, "brand": "Mamaearth", "source": "amazon", "sample_reviews": "broken hair"}
    ]
    pd.DataFrame(pain_data).to_csv(reports_dir / "customer_pain_points.csv", index=False)
    
    # 5. customer_praise_points.csv
    praise_data = [
        {"topic": "Effective Ingredients", "frequency": 1, "brand": "Minimalist", "source": "amazon", "sample_reviews": "loved niacinamide"}
    ]
    pd.DataFrame(praise_data).to_csv(reports_dir / "customer_praise_points.csv", index=False)
    
    # 6. topic_gap_analysis.csv
    gap_data = [
        {"Topic": "Hair Fall", "Mamaearth": 2, "Minimalist": 0, "Gap": "+2"},
        {"Topic": "Effective Ingredients", "Mamaearth": 0, "Minimalist": 1, "Gap": "-1"}
    ]
    pd.DataFrame(gap_data).to_csv(reports_dir / "topic_gap_analysis.csv", index=False)
    
    # 7. topic_sentiment_matrix.csv
    matrix_data = [
        {"topic": "Hair Fall", "negative_count": 2, "positive_count": 0, "neutral_count": 0},
        {"topic": "Effective Ingredients", "negative_count": 0, "positive_count": 1, "neutral_count": 0}
    ]
    pd.DataFrame(matrix_data).to_csv(reports_dir / "topic_sentiment_matrix.csv", index=False)
    
    # 8. executive_brief.md
    brief_content = """# Executive Briefing: Brand Sentiment & Competitor Intelligence

## 1. Key Findings
* **Competitive Divide**: Minimalist leads digital advocacy.
* **Core Product Issues**: Packaging dropper leak complaints.

## 4. Competitor Strengths
* **Minimalist**: High customer trust in chemical ingredients.
* **Mamaearth**: Gentle Aloe Vera cleansers.

## 5. Competitor Weaknesses
* **Minimalist**: Sunscreen SPF 50 white cast.
* **Mamaearth**: Onion shampoo hair fall.
"""
    with open(reports_dir / "executive_brief.md", "w", encoding="utf-8") as f:
        f.write(brief_content)

    # 9. recommendations.md
    recs_content = """# Strategic Business Recommendations

## Topic: Hair Fall
* **Observation**: Onion shampoo is linked to hair fall.
* **Evidence**: 1 review reports hair shedding.
* **Recommendation**: Conduct clinic safety audits.
* **Recommendation Confidence**: **Low**
"""
    with open(reports_dir / "recommendations.md", "w", encoding="utf-8") as f:
        f.write(recs_content)
        
    # 10. competitor_intelligence.md
    with open(reports_dir / "competitor_intelligence.md", "w", encoding="utf-8") as f:
        f.write("# Competitor Sentiment & Voice of Customer Intelligence Report\nMock intelligence details here.")
        
    # 11. model_performance.md
    perf_content = """# Model Performance Audit Report
## 1. Execution Diagnostics
| Metric | Value |
| :--- | :--- |
| **Model Name** | `RoBERTa (cardiffnlp)` |
| **Throughput Rate** | 1.23 records/second |
| **Fallback Usage Percentage** | 10.0% |
"""
    with open(reports_dir / "model_performance.md", "w", encoding="utf-8") as f:
        f.write(perf_content)
        
    # 12. topic_model_performance.md
    topic_perf_content = """# Topic Modeling Performance Report
## 1. Execution Diagnostics
| Metric | Value |
| :--- | :--- |
| **Model Type (Positive)** | `NMF Fallback` |
| **Model Type (Negative)** | `Lexical Category Fallback` |
| **Topics Discovered (Positive)** | 1 |
| **Topics Discovered (Negative)** | 1 |
"""
    with open(reports_dir / "topic_model_performance.md", "w", encoding="utf-8") as f:
        f.write(topic_perf_content)
        
    return str(reports_dir), str(data_dir)


def test_models_serialization() -> None:
    # 1. SentimentSummary
    summary = SentimentSummary(brand="Mamaearth", total_records=10, positive_pct=60.0, neutral_pct=20.0, negative_pct=20.0, net_sentiment=40.0)
    summary_dict = summary.to_dict()
    assert summary_dict["brand"] == "Mamaearth"
    assert summary_dict["net_sentiment"] == 40.0

    # 2. TopicGap
    gap = TopicGap(topic="Hair Fall", mamaearth=2, minimalist=0, gap=2)
    assert gap.to_dict()["gap"] == 2

    # 3. Recommendation
    rec = Recommendation(topic="Hair Fall", observation="O", evidence="E", recommendation="R", confidence="Low")
    assert rec.to_dict()["confidence"] == "Low"

    # 4. DashboardData
    dash = DashboardData(title="T", metrics={"m": 1}, tables={"t": [{"col": 2}]}, metadata={"k": "v"})
    assert dash.to_dict()["title"] == "T"


def test_sentiment_service(mock_reports_dir) -> None:
    reports_dir, data_dir = mock_reports_dir
    
    # Test get_sentiment_summary
    summary_df = get_sentiment_summary(reports_dir)
    assert not summary_df.empty
    assert len(summary_df) == 3
    assert "brand" in summary_df.columns
    
    # Test get_brand_sentiment
    brand_df = get_brand_sentiment(data_dir)
    assert not brand_df.empty
    # Mamaearth has 2, Minimalist has 1
    assert len(brand_df) == 2
    mama_row = brand_df[brand_df["brand"] == "Mamaearth"].iloc[0]
    assert mama_row["total_records"] == 2
    assert mama_row["positive"] == 1
    assert mama_row["negative"] == 1
    assert mama_row["net_sentiment"] == 0.0  # 1 pos, 1 neg -> net = 0
    
    # Test get_source_sentiment
    source_df = get_source_sentiment(reports_dir)
    assert not source_df.empty
    assert len(source_df) == 3
    
    # Test get_sentiment_trends
    trends_df = get_sentiment_trends(data_dir)
    assert not trends_df.empty
    assert "year_month" in trends_df.columns
    assert "net_sentiment" in trends_df.columns


def test_topic_service(mock_reports_dir) -> None:
    reports_dir, _ = mock_reports_dir
    
    # Test complaints and praises
    assert len(get_top_complaints(reports_dir)) == 1
    assert len(get_top_praise(reports_dir)) == 1
    
    # Test combined distribution
    dist_df = get_topic_distribution(reports_dir)
    assert len(dist_df) == 2
    assert set(dist_df["type"].tolist()) == {"Complaint", "Praise"}
    
    # Test sentiment matrix
    matrix_df = get_topic_sentiment_matrix(reports_dir)
    assert len(matrix_df) == 2
    assert "negative_count" in matrix_df.columns


def test_competitor_service(mock_reports_dir) -> None:
    reports_dir, _ = mock_reports_dir
    
    # Test competitor comparison
    comparison = get_competitor_comparison(reports_dir)
    assert "Intelligence Report" in comparison
    
    # Test gaps
    gaps_df = get_topic_gaps(reports_dir)
    assert len(gaps_df) == 2
    
    # Test brand strengths & weaknesses parser
    strengths = get_brand_strengths(reports_dir)
    assert "Minimalist" in strengths
    assert "Mamaearth" in strengths
    assert strengths["Minimalist"][0] == "High customer trust in chemical ingredients."
    
    weaknesses = get_brand_weaknesses(reports_dir)
    assert weaknesses["Mamaearth"][0] == "Onion shampoo hair fall."


def test_executive_service(mock_reports_dir) -> None:
    reports_dir, _ = mock_reports_dir
    
    # Test summary raw read
    summary = get_executive_summary(reports_dir)
    assert "Executive Briefing" in summary
    
    # Test key findings
    findings = get_key_findings(reports_dir)
    assert len(findings) == 2
    assert findings[0] == "Competitive Divide: Minimalist leads digital advocacy."
    
    # Test recommendations parser
    recs_df = get_recommendations(reports_dir)
    assert len(recs_df) == 1
    assert recs_df.iloc[0]["topic"] == "Hair Fall"
    assert recs_df.iloc[0]["confidence"] == "Low"


def test_dashboard_service(mock_reports_dir) -> None:
    reports_dir, data_dir = mock_reports_dir
    
    # 1. Executive dashboard data
    exec_data = get_executive_dashboard_data(reports_dir)
    assert exec_data["title"] == "Executive Briefing Dashboard"
    assert len(exec_data["key_findings"]) == 2
    assert "Mamaearth" in exec_data["brand_sentiments"]
    assert exec_data["brand_sentiments"]["Mamaearth"]["net_sentiment"] == 40.0
    
    # 2. Sentiment dashboard data
    sent_data = get_sentiment_dashboard_data(reports_dir, data_dir)
    assert sent_data["title"] == "Brand Sentiment Performance Dashboard"
    assert sent_data["sentiment_gap"] == 30.0
    assert len(sent_data["source_breakdown"]) == 3
    
    # 3. VoC dashboard data
    voc_data = get_voc_dashboard_data(reports_dir)
    assert voc_data["title"] == "Voice of the Customer (VoC) Analysis Dashboard"
    assert len(voc_data["top_complaints"]) == 1
    assert len(voc_data["top_praise"]) == 1
    
    # 4. Competitor dashboard data
    comp_data = get_competitor_dashboard_data(reports_dir)
    assert comp_data["title"] == "Competitor Intelligence & Gap Analysis Dashboard"
    assert len(comp_data["topic_gaps"]) == 2
    assert comp_data["brand_strengths"]["Minimalist"][0] == "High customer trust in chemical ingredients."


def test_health_service(mock_reports_dir, tmp_path) -> None:
    reports_dir, _ = mock_reports_dir
    db_file = tmp_path / "test_health.db"
    db_helper = DatabaseHelper(str(db_file))
    
    # Log a mock run
    db_helper.log_collection_run("2026-06-11T12:00:00", "SUCCESS", 10, 30, "All OK")
    
    # Populate mock posts / comments
    brand_map = db_helper.insert_brands(["Mamaearth", "Minimalist"])
    posts = [
        {"id": "p1", "brand_id": brand_map["Mamaearth"], "title": "T", "body": "B", "subreddit": "skincare", "score": 10, "author": "auth1", "created_utc": 1680000000, "source": "reddit", "rating": None}
    ]
    comments = [
        {"id": "c1", "post_id": "p1", "brand_id": brand_map["Mamaearth"], "body": "B", "subreddit": "skincare", "score": 5, "author": "auth2", "created_utc": 1680000100, "source": "reddit", "rating": None}
    ]
    db_helper.upsert_posts(posts)
    db_helper.upsert_comments(comments)
    
    # 1. Pipeline health
    health_df = get_pipeline_health(str(db_file))
    assert not health_df.empty
    assert len(health_df) == 1
    assert health_df.iloc[0]["status"] == "SUCCESS"
    
    # 2. Dataset summary counts
    summary = get_dataset_summary(str(db_file))
    assert summary["total_posts"] == 1
    assert summary["total_comments"] == 1
    assert summary["unique_authors"] == 2
    assert summary["unique_subreddits"] == 1
    
    # 3. Model performance summaries
    model_summary = get_model_summary(reports_dir)
    assert model_summary["sentiment_model"] == "RoBERTa (cardiffnlp)"
    assert model_summary["sentiment_throughput_sec"] == 1.23
    assert model_summary["sentiment_fallback_usage_pct"] == 10.0
    assert model_summary["topic_model_positive"] == "NMF Fallback"
    assert model_summary["topic_model_negative"] == "Lexical Category Fallback"
    assert model_summary["topics_pos_count"] == 1


def test_service_caching_behavior(mock_reports_dir) -> None:
    reports_dir, _ = mock_reports_dir
    file_path = os.path.join(reports_dir, "sentiment_summary.csv")
    
    # Reset cache before testing
    clear_sentiment_cache()
    
    info_start = _read_csv_cached.cache_info()
    
    # First call: cache miss (reads file)
    get_sentiment_summary(reports_dir)
    info_first = _read_csv_cached.cache_info()
    assert info_first.misses == info_start.misses + 1
    
    # Second call: cache hit (reads memory)
    get_sentiment_summary(reports_dir)
    info_second = _read_csv_cached.cache_info()
    assert info_second.hits == info_first.hits + 1
    
    # Cache clear
    clear_sentiment_cache()
    info_cleared = _read_csv_cached.cache_info()
    assert info_cleared.hits == 0
    assert info_cleared.misses == 0
