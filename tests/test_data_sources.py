import os
import pandas as pd
import pytest
from src.data_sources.csv_source import CSVSource
from src.data_sources.reddit_source import RedditSource

@pytest.fixture
def mock_csv_file(tmp_path) -> str:
    csv_file = tmp_path / "reviews_test.csv"
    data = [
        {
            "review_id": "r1",
            "brand_name": "Mamaearth",
            "headline": "Terrible Onion Shampoo",
            "review_text": "Causes hairfall clumps.",
            "stars": 1.0,
            "reviewer": "user1",
            "review_date": "2023-01-01"
        },
        {
            "review_id": "r2",
            "brand_name": "Minimalist",
            "headline": "Great niacinamide",
            "review_text": "Cleared my dark spots.",
            "stars": 5.0,
            "reviewer": "user2",
            "review_date": "2023-02-01"
        }
    ]
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False)
    return str(csv_file)

def test_csv_source_ingestion_and_brand_filtering(mock_csv_file: str) -> None:
    csv_source = CSVSource()
    
    # 1. Fetch data for Mamaearth
    mama_records = csv_source.fetch_data("Mamaearth", csv_path=mock_csv_file, source_name="amazon")
    assert len(mama_records) == 1
    rec = mama_records[0]
    assert rec["source"] == "amazon"
    assert rec["source_record_id"] == "r1"
    assert rec["brand"] == "Mamaearth"
    assert rec["title"] == "Terrible Onion Shampoo"
    assert rec["text"] == "Causes hairfall clumps."
    assert rec["rating"] == 1.0
    assert rec["author"] == "user1"
    assert isinstance(rec["created_at"], float)

    # 2. Fetch data for Minimalist
    mini_records = csv_source.fetch_data("Minimalist", csv_path=mock_csv_file, source_name="nykaa")
    assert len(mini_records) == 1
    assert mini_records[0]["source"] == "nykaa"
    assert mini_records[0]["source_record_id"] == "r2"
    assert mini_records[0]["rating"] == 5.0

def test_reddit_source_availability(monkeypatch) -> None:
    # Disable config credentials to ensure RedditSource initializes as unavailable
    import src.utils.config as cfg
    monkeypatch.setattr(cfg.config, "reddit_client_id", "")
    monkeypatch.setattr(cfg.config, "reddit_client_secret", "")
    
    reddit_source = RedditSource()
    assert reddit_source.available is False
    
    # fetch_data should return an empty list when unavailable
    res = reddit_source.fetch_data("Mamaearth")
    assert res == []
