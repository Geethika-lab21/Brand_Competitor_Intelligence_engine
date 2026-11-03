import os
import time
import datetime
import pandas as pd
from src.utils.logger import logger
from src.utils.config import config
from src.utils.database_helper import DatabaseHelper
from src.data_sources.reddit_source import RedditSource
from src.data_sources.csv_source import CSVSource
from src.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.sentiment.sentiment_reports import generate_sentiment_reports
from src.sentiment.sentiment_visualizations import generate_sentiment_visualizations

def ensure_mock_amazon_csv() -> str:
    """
    Creates a mock Amazon skincare reviews CSV to demonstrate the Multi-Source
    CSVSource ingestion pipeline in action.
    """
    mock_file = "data/amazon_reviews_mock.csv"
    if os.path.exists(mock_file):
        return mock_file
        
    logger.info("Generating mock Amazon reviews CSV at data/amazon_reviews_mock.csv...")
    os.makedirs(os.path.dirname(mock_file), exist_ok=True)
    
    now = time.time()
    mock_reviews = [
        # Mamaearth
        {
            "review_id": "amz_mama_0",
            "brand": "Mamaearth",
            "review_title": "Onion shampoo caused severe hairfall",
            "review_text": "I used this shampoo for three wash cycles. My hair started falling out in clumps. Extremely disappointed with the quality.",
            "rating": 1.0,
            "reviewer_name": "ananya_r",
            "review_date": datetime.datetime.utcfromtimestamp(now - 86400 * 30).isoformat()
        },
        {
            "review_id": "amz_mama_1",
            "brand": "Mamaearth",
            "review_title": "Ubtan face wash is decent",
            "review_text": "It washes off oil well, but feels dry after use. Average product, heavily advertised by influencers.",
            "rating": 3.0,
            "reviewer_name": "rahul_k",
            "review_date": datetime.datetime.utcfromtimestamp(now - 86400 * 20).isoformat()
        },
        {
            "review_id": "amz_mama_2",
            "brand": "Mamaearth",
            "review_title": "Very refreshing moisturizer",
            "review_text": "The vitamin C oil free moisturizer is lightweight and hydrating. Smells nice and matches my oily skin.",
            "rating": 4.0,
            "reviewer_name": "riya_s",
            "review_date": datetime.datetime.utcfromtimestamp(now - 86400 * 10).isoformat()
        },
        
        # Minimalist
        {
            "review_id": "amz_mini_0",
            "brand": "Minimalist",
            "review_title": "Active Niacinamide serum works miracles",
            "review_text": "I have been using this 10% Niacinamide serum. It completely cleared my dark spots and acne scars in 3 weeks! Holy grail product.",
            "rating": 5.0,
            "reviewer_name": "priya_m",
            "review_date": datetime.datetime.utcfromtimestamp(now - 86400 * 25).isoformat()
        },
        {
            "review_id": "amz_mini_1",
            "brand": "Minimalist",
            "review_title": "Sunscreen leaves a white cast",
            "review_text": "The SPF 50 sunscreen is too heavy and sticky. It leaves a visible white cast and makes my oily skin sweat a lot.",
            "rating": 2.0,
            "reviewer_name": "vikram_d",
            "review_date": datetime.datetime.utcfromtimestamp(now - 86400 * 15).isoformat()
        },
        {
            "review_id": "amz_mini_2",
            "brand": "Minimalist",
            "review_title": "Salicylic acid cleanser is effective",
            "review_text": "Great face wash for acne control. Keeps oil in check without stripping skin barriers. Will repurchase.",
            "rating": 4.5,
            "reviewer_name": "neha_p",
            "review_date": datetime.datetime.utcfromtimestamp(now - 86400 * 5).isoformat()
        }
    ]
    
    df = pd.DataFrame(mock_reviews)
    df.to_csv(mock_file, index=False, encoding="utf-8")
    return mock_file

def run_sentiment_pipeline() -> None:
    """
    Main orchestrator for Phase 4 Multi-Source Sentiment Engine:
    1. Sets up data sources (Reddit PRAW + Local CSV reviews).
    2. Standardizes ingested records.
    3. Runs RoBERTa sentiment classifier (with lexicon fallbacks).
    4. Computes performance throughput audits.
    5. Saves predictions CSV, brand metrics, and Plotly graphics.
    """
    logger.info("==========================================")
    logger.info("Starting Multi-Source Sentiment Analysis Pipeline")
    logger.info("==========================================")
    
    start_time = time.time()
    db_helper = DatabaseHelper(config.database_path)
    
    # 1. Determine dataset path and brands dynamically
    csv_path = "data/nyka_top_brands_cosmetics_product_reviews.csv"
    if not os.path.exists(csv_path):
        logger.error(f"Nykaa dataset not found at: {csv_path}. Sentiment pipeline aborted.")
        return
        
    df_raw = pd.read_csv(csv_path)
    brands = sorted(df_raw["brand_name"].dropna().unique().tolist())
    
    # 2. Initialize Ingestion Sources
    reddit_source = RedditSource(db_helper=db_helper)
    csv_source = CSVSource(default_source_name="nykaa")
    
    raw_records = []
 
    # 3. Fetch Data across Brands and Sources
    for brand in brands:
        # A. Reddit Ingestion (If available)
        if reddit_source.available:
            reddit_data = reddit_source.fetch_data(brand, limit_per_query=20)
            raw_records.extend(reddit_data)
        else:
            logger.debug(f"Reddit client credentials not loaded. Skipping Reddit ingestion for {brand}.")
            
        # B. CSV reviews Ingestion (Always available)
        csv_data = csv_source.fetch_data(brand, csv_path=csv_path, source_name="nykaa")
        raw_records.extend(csv_data)
 
    if not raw_records:
        logger.warning("No records ingested from any source. Sentiment pipeline aborted.")
        return
 
    logger.info(f"Ingested {len(raw_records)} total records from data sources. Beginning sentiment classification...")
 
    # 4. Initialize Sentiment Analyzer - ENFORCE FALLBACK FOR SPEED
    analyzer = SentimentAnalyzer(force_fallback=True)
    
    processed_records = []
    
    # 5. Run sentiment classifications
    for rec in raw_records:
        # Combine title and text to enrich context for the classifier
        title_text = f"{rec['title']} " if rec.get("title") else ""
        full_text = f"{title_text}{rec['text']}"
        
        # Run classification
        sentiment_res = analyzer.analyze_text(full_text)
        
        # Merge results with base standardized schema
        analyzed_rec = rec.copy()
        analyzed_rec.update(sentiment_res)
        processed_records.append(analyzed_rec)

    # 6. Performance calculation
    end_time = time.time()
    elapsed_seconds = end_time - start_time
    diagnostics = analyzer.get_diagnostics()

    # Convert results to DataFrame
    results_df = pd.DataFrame(processed_records)

    # 7. Generate Reports & Visualizations
    reports_dir = "reports"
    data_dir = "data"
    figures_dir = os.path.join(reports_dir, "figures")

    # Generate CSV summaries & MD audits
    generate_sentiment_reports(
        results_df=results_df,
        diagnostics=diagnostics,
        processing_time=elapsed_seconds,
        reports_dir=reports_dir,
        data_dir=data_dir,
        db_helper=db_helper
    )

    # Generate Plotly charts
    generate_sentiment_visualizations(results_df, figures_dir)

    logger.info("==========================================")
    logger.info("Sentiment Intelligence Pipeline Completed Successfully!")
    logger.info("==========================================")

if __name__ == "__main__":
    run_sentiment_pipeline()
