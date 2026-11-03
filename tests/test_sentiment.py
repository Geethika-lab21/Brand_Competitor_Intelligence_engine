import pandas as pd
import pytest
from src.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.sentiment.sentiment_metrics import calculate_sentiment_metrics

def test_lexicon_fallback_classification() -> None:
    # Initialize analyzer with forced fallback to test lexicon rules offline
    analyzer = SentimentAnalyzer(force_fallback=True)
    
    # 1. Test positive phrase classification
    res_pos = analyzer.analyze_text("This serum is amazing! I love how my skin is glowing.")
    assert res_pos["sentiment_label"] == "positive"
    assert res_pos["sentiment_score"] == 1.0
    assert res_pos["sentiment_confidence"] > 0.0
    
    # 2. Test negative phrase classification
    res_neg = analyzer.analyze_text("Horrible experience. Onion shampoo caused extreme hairfall and clumps.")
    assert res_neg["sentiment_label"] == "negative"
    assert res_neg["sentiment_score"] == -1.0
    
    # 3. Test neutral phrase classification
    res_neu = analyzer.analyze_text("The bottle contains 50ml of moisturizer.")
    assert res_neu["sentiment_label"] == "neutral"
    assert res_neu["sentiment_score"] == 0.0

def test_sentiment_metrics_calculator() -> None:
    # Build mock predictions dataframe
    data = [
        {"brand": "Mamaearth", "sentiment_label": "positive"},
        {"brand": "Mamaearth", "sentiment_label": "positive"},
        {"brand": "Mamaearth", "sentiment_label": "positive"},
        {"brand": "Mamaearth", "sentiment_label": "positive"},
        {"brand": "Mamaearth", "sentiment_label": "negative"}, # 4 Pos, 1 Neg -> Net: (3/5)*100 = 60%
        
        {"brand": "Minimalist", "sentiment_label": "positive"},
        {"brand": "Minimalist", "sentiment_label": "neutral"},
        {"brand": "Minimalist", "sentiment_label": "negative"} # 1 Pos, 1 Neu, 1 Neg -> Net: 0%
    ]
    df = pd.DataFrame(data)
    
    metrics_df = calculate_sentiment_metrics(df, groupby_col="brand")
    assert not metrics_df.empty
    
    # Check Mamaearth metrics
    mama_stats = metrics_df[metrics_df["brand"] == "Mamaearth"].iloc[0]
    assert mama_stats["total_records"] == 5
    assert mama_stats["positive_pct"] == 80.0
    assert mama_stats["negative_pct"] == 20.0
    assert mama_stats["net_sentiment"] == 60.0
    
    # Check Minimalist metrics
    mini_stats = metrics_df[metrics_df["brand"] == "Minimalist"].iloc[0]
    assert mini_stats["total_records"] == 3
    assert mini_stats["positive_pct"] == 33.33
    assert mini_stats["net_sentiment"] == 0.0

def test_sentiment_reports_generation(tmp_path) -> None:
    from src.sentiment.sentiment_reports import generate_sentiment_reports
    from src.utils.database_helper import DatabaseHelper
    import os

    # 1. Setup temporary directories and database helper
    reports_dir = tmp_path / "reports"
    data_dir = tmp_path / "data"
    db_file = tmp_path / "test_sentiment_predictions.db"
    db_helper = DatabaseHelper(str(db_file))

    # 2. Build mock predictions dataframe
    data = [
        # Mamaearth: 2 Pos, 1 Neg -> Net Sentiment: (2 - 1)/3 * 100 = 33.33
        {"source_record_id": "r1", "source": "amazon", "brand": "Mamaearth", "sentiment_label": "positive", "sentiment_score": 1.0, "sentiment_confidence": 0.85},
        {"source_record_id": "r2", "source": "amazon", "brand": "Mamaearth", "sentiment_label": "positive", "sentiment_score": 1.0, "sentiment_confidence": 0.90},
        {"source_record_id": "r3", "source": "amazon", "brand": "Mamaearth", "sentiment_label": "negative", "sentiment_score": -1.0, "sentiment_confidence": 0.95},

        # Minimalist: 3 Pos, 1 Neg -> Net Sentiment: (3 - 1)/4 * 100 = 50.00
        {"source_record_id": "r4", "source": "amazon", "brand": "Minimalist", "sentiment_label": "positive", "sentiment_score": 1.0, "sentiment_confidence": 0.99},
        {"source_record_id": "r5", "source": "amazon", "brand": "Minimalist", "sentiment_label": "positive", "sentiment_score": 1.0, "sentiment_confidence": 0.92},
        {"source_record_id": "r6", "source": "amazon", "brand": "Minimalist", "sentiment_label": "positive", "sentiment_score": 1.0, "sentiment_confidence": 0.70}, # low confidence pos
        {"source_record_id": "r7", "source": "amazon", "brand": "Minimalist", "sentiment_label": "negative", "sentiment_score": -1.0, "sentiment_confidence": 0.88}
    ]
    df = pd.DataFrame(data)

    diagnostics = {"model_name": "TestModel", "fallback_usage_pct": 0.0}

    # 3. Generate reports
    generate_sentiment_reports(
        results_df=df,
        diagnostics=diagnostics,
        processing_time=1.5,
        reports_dir=str(reports_dir),
        data_dir=str(data_dir),
        db_helper=db_helper
    )

    # 4. Verify Brand Sentiment Gap in sentiment_summary.csv
    summary_file = reports_dir / "sentiment_summary.csv"
    assert os.path.exists(summary_file)
    summary_df = pd.read_csv(summary_file)
    
    # Net Sentiment details:
    # Minimalist net: 50.00
    # Mamaearth net: 33.33
    # Gap = 50.00 - 33.33 = 16.67
    gap_row = summary_df[summary_df["brand"] == "Brand Sentiment Gap (Minimalist - Mamaearth)"]
    assert len(gap_row) == 1
    assert abs(gap_row.iloc[0]["net_sentiment"] - 16.67) < 0.1

    # 5. Verify High Confidence files are generated
    high_pos_file = reports_dir / "high_confidence_positive.csv"
    high_neg_file = reports_dir / "high_confidence_negative.csv"
    assert os.path.exists(high_pos_file)
    assert os.path.exists(high_neg_file)

    high_pos_df = pd.read_csv(high_pos_file)
    # Expected high confidence pos: r1, r2, r4, r5 (confidence >= 0.80). r6 (0.70) is excluded.
    assert len(high_pos_df) == 4
    assert set(high_pos_df["source_record_id"].tolist()) == {"r1", "r2", "r4", "r5"}

    high_neg_df = pd.read_csv(high_neg_file)
    # Expected high confidence neg: r3, r7 (confidence >= 0.80)
    assert len(high_neg_df) == 2
    assert set(high_neg_df["source_record_id"].tolist()) == {"r3", "r7"}

    # 6. Verify SQLite database insertion
    conn = db_helper.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sentiment_predictions;")
    db_rows = cursor.fetchall()
    conn.close()

    assert len(db_rows) == 7
    # Check that a specific record has all fields
    r1_db = next(r for r in db_rows if r["source_record_id"] == "r1")
    assert r1_db["source"] == "amazon"
    assert r1_db["brand"] == "Mamaearth"
    assert r1_db["sentiment_label"] == "positive"
    assert r1_db["sentiment_score"] == 1.0
    assert r1_db["sentiment_confidence"] == 0.85
    assert r1_db["prediction_timestamp"] is not None
