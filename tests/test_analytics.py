import os
import sqlite3
import pandas as pd
import pytest
from typing import Tuple
from src.utils.database_helper import DatabaseHelper
from src.analytics.data_quality import DataQualityAnalyzer
from src.analytics.exploratory_analysis import ExploratoryAnalyzer

@pytest.fixture
def temp_db_helper(tmp_path) -> DatabaseHelper:
    db_file = tmp_path / "test_brand_intel_analytics.db"
    helper = DatabaseHelper(str(db_file))
    
    # Insert mock data
    brand_map = helper.insert_brands(["Mamaearth", "Minimalist"])
    
    posts = [
        {
            "id": "post1",
            "brand_id": brand_map["Mamaearth"],
            "title": "Mamaearth onion shampoo is terrible",
            "body": "It caused massive hair fall.",
            "subreddit": "IndianSkincareAddicts",
            "score": 10,
            "author": "skin_user1",
            "created_utc": 1680000000.0, # March 2023
            "source": "reddit",
            "rating": None
        },
        {
            "id": "post2",
            "brand_id": brand_map["Minimalist"],
            "title": "Minimalist Niacinamide serum",
            "body": "This serum is great for acne. Mamaearth products are not as transparent.",
            "subreddit": "IndianSkincareAddicts",
            "score": 20,
            "author": "skin_user2",
            "created_utc": 1682000000.0, # April 2023
            "source": "reddit",
            "rating": None
        },
        {
            "id": "post3",
            "brand_id": brand_map["Minimalist"],
            "title": "Comparison: Mamaearth Vitamin C vs Minimalist Vitamin C",
            "body": "I want to compare Mamaearth and Minimalist serums.",
            "subreddit": "SkincareAddiction",
            "score": 15,
            "author": "skin_user1",
            "created_utc": 1682500000.0, # April 2023
            "source": "reddit",
            "rating": None
        }
    ]
    
    comments = [
        {
            "id": "comm1",
            "post_id": "post1",
            "brand_id": brand_map["Mamaearth"],
            "body": "Had the exact same experience with onion oil shampoo.",
            "subreddit": "IndianSkincareAddicts",
            "score": 5,
            "author": "skin_user3",
            "created_utc": 1680000100.0,
            "source": "reddit",
            "rating": None
        },
        {
            "id": "comm2",
            "post_id": "post2",
            "brand_id": brand_map["Minimalist"],
            "body": "Yes, Minimalist niacinamide works well.",
            "subreddit": "IndianSkincareAddicts",
            "score": 12,
            "author": "skin_user1",
            "created_utc": 1682000100.0,
            "source": "reddit",
            "rating": None
        }
    ]
    
    helper.upsert_posts(posts)
    helper.upsert_comments(comments)
    return helper

@pytest.fixture
def temp_csv_files(tmp_path) -> Tuple[str, str]:
    posts_path = tmp_path / "preprocessed_posts.csv"
    comments_path = tmp_path / "preprocessed_comments.csv"
    
    posts_df = pd.DataFrame({
        "id": ["post1", "post2", "post3"],
        "brand_name": ["Mamaearth", "Minimalist", "Minimalist"],
        "title": ["Mamaearth onion shampoo is terrible", "Minimalist Niacinamide serum", "Comparison: Mamaearth vs Minimalist"],
        "clean_text": [
            "mamaearth onion shampoo terrible caused massive hair fall",
            "minimalist niacinamide serum serum great acne mamaearth product transparent",
            "comparison mamaearth vitamin c vs minimalist vitamin c compare mamaearth minimalist serum"
        ]
    })
    
    comments_df = pd.DataFrame({
        "id": ["comm1", "comm2"],
        "brand_name": ["Mamaearth", "Minimalist"],
        "body": ["Had the exact same experience with onion oil shampoo.", "Yes, Minimalist niacinamide works well."],
        "clean_text": [
            "exact experience onion oil shampoo",
            "yes minimalist niacinamide work well"
        ]
    })
    
    posts_df.to_csv(posts_path, index=False)
    comments_df.to_csv(comments_path, index=False)
    
    return str(posts_path), str(comments_path)

def test_data_quality_analyzer(temp_db_helper: DatabaseHelper) -> None:
    analyzer = DataQualityAnalyzer(temp_db_helper)
    metrics = analyzer.compute_quality_metrics()
    
    assert metrics is not None
    summary = metrics.get("summary", {})
    assert summary.get("total_posts") == 3
    assert summary.get("total_comments") == 2
    assert summary.get("total_brands") == 2
    # Unique authors: skin_user1, skin_user2, skin_user3 -> 3 unique
    assert summary.get("unique_authors") == 3
    # Subreddits: IndianSkincareAddicts, SkincareAddiction -> 2 unique
    assert summary.get("unique_subreddits") == 2
    assert summary.get("avg_post_score") == 15.0 # (10+20+15)/3
    assert summary.get("avg_comment_score") == 8.5 # (5+12)/2
    assert summary.get("duplicate_posts") == 0
    assert summary.get("duplicate_comments") == 0
    
    # Check null count structure
    missing = metrics.get("missing_values", {})
    assert "id" in missing.get("posts", {})
    assert missing.get("posts", {}).get("rating") == 3 # All ratings are null

def test_exploratory_analyzer_brand_and_subreddit(temp_db_helper: DatabaseHelper, temp_csv_files, tmp_path) -> None:
    posts_csv, comments_csv = temp_csv_files
    reports_dir = tmp_path / "reports"
    
    analyzer = ExploratoryAnalyzer(temp_db_helper, posts_csv, comments_csv)
    
    # Brand Analytics
    brand_summary = analyzer.generate_brand_analytics(str(reports_dir))
    assert not brand_summary.empty
    assert "brand" in brand_summary.columns
    # Check co-mention output
    comentions_csv = reports_dir / "brand_comentions.csv"
    assert os.path.exists(comentions_csv)
    comentions_df = pd.read_csv(comentions_csv)
    # Post 2 and Post 3 mentions both Mamaearth and Minimalist
    assert len(comentions_df) == 2

    # Subreddit Analytics
    sub_posts, sub_summary = analyzer.generate_subreddit_analytics(str(reports_dir))
    assert not sub_summary.empty
    assert "subreddit" in sub_summary.columns
    assert os.path.exists(reports_dir / "subreddit_summary.csv")

def test_exploratory_analyzer_text_and_tfidf(temp_db_helper: DatabaseHelper, temp_csv_files, tmp_path) -> None:
    posts_csv, comments_csv = temp_csv_files
    reports_dir = tmp_path / "reports"
    
    analyzer = ExploratoryAnalyzer(temp_db_helper, posts_csv, comments_csv)
    
    # Text Analytics N-grams
    text_stats = analyzer.generate_text_analytics(str(reports_dir))
    assert "unigrams" in text_stats
    assert "bigrams" in text_stats
    assert "trigrams" in text_stats
    assert not text_stats["unigrams"].empty
    assert os.path.exists(reports_dir / "word_frequency.csv")
    assert os.path.exists(reports_dir / "bigram_frequency.csv")
    
    # TF-IDF Analytics
    tfidf_mama, tfidf_mini = eda_tfidf = analyzer.generate_tfidf_analytics(str(reports_dir))
    assert os.path.exists(reports_dir / "tfidf_mamaearth.csv")
    assert os.path.exists(reports_dir / "tfidf_minimalist.csv")
    # Verify TF-IDF outputs contain words
    assert not tfidf_mama.empty
    assert not tfidf_mini.empty
    assert "word" in tfidf_mama.columns
    assert "tfidf_score" in tfidf_mama.columns

def test_exploratory_analyzer_time_series(temp_db_helper: DatabaseHelper, temp_csv_files, tmp_path) -> None:
    posts_csv, comments_csv = temp_csv_files
    reports_dir = tmp_path / "reports"
    figures_dir = tmp_path / "reports" / "figures"
    
    analyzer = ExploratoryAnalyzer(temp_db_helper, posts_csv, comments_csv)
    
    # Time Series Analytics
    posts_time, comments_time = analyzer.generate_time_series_analytics(str(reports_dir))
    assert os.path.exists(reports_dir / "posts_per_month.csv")
    assert os.path.exists(reports_dir / "comments_per_month.csv")
    assert not posts_time.empty
    assert "year_month" in posts_time.columns
    # Check grouping: '2023-03' and '2023-04'
    months = posts_time["year_month"].tolist()
    assert "2023-03" in months
    assert "2023-04" in months

    # Generate Visualizations (should not throw exceptions)
    text_stats = analyzer.generate_text_analytics(str(reports_dir))
    analyzer.generate_visualizations(str(figures_dir), text_stats, posts_time, comments_time)
    
    assert os.path.exists(figures_dir / "posts_by_brand.html")
    assert os.path.exists(figures_dir / "comments_by_brand.html")
    assert os.path.exists(figures_dir / "posts_over_time.html")
    assert os.path.exists(figures_dir / "comments_over_time.html")
