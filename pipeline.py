import os
import datetime
import pandas as pd
from src.utils.logger import logger
from src.utils.config import config
from src.utils.database_helper import DatabaseHelper
from src.data_collection.reddit_collector import RedditCollector
from src.preprocessing.text_preprocessing import TextPreprocessor

def run_pipeline() -> None:
    """
    Orchestrates the entire Phase 1 pipeline:
    1. Initialize database and log run start.
    2. Collect Reddit posts & comments for configured brands.
    3. Save raw data to CSV files.
    4. Save raw data to SQLite database.
    5. Preprocess text (in-memory) and show preview.
    6. Save preprocessed outputs to CSV for future NLP phases.
    """
    logger.info("========================================")
    logger.info("Starting Brand & Competitor Intelligence Engine Pipeline")
    logger.info("========================================")
    
    # 1. Initialize SQLite Database Helper
    db_helper = DatabaseHelper(config.database_path)
    
    # Start tracking run
    run_timestamp = datetime.datetime.utcnow().isoformat()
    run_id = db_helper.log_collection_run(
        timestamp=run_timestamp,
        status="RUNNING",
        posts_collected=0,
        comments_collected=0,
        details="Pipeline execution started."
    )
    logger.info(f"Initialized Pipeline Run ID: {run_id} in SQLite monitoring.")

    all_posts = []
    all_comments = []

    try:
        # 2. Collect Data
        collector = RedditCollector(db_helper=db_helper)
        
        for brand_name in config.brands_search_terms.keys():
            # Fetch posts (PRAW or Mock)
            posts = collector.fetch_brand_posts(brand_name, limit_per_term=10)
            logger.info(f"Collected {len(posts)} unique posts for brand '{brand_name}'")
            all_posts.extend(posts)
            
            # Fetch comments for each post
            for post in posts:
                comments = collector.fetch_comments(post["id"], brand_name, max_comments=5)
                all_comments.extend(comments)
                
        logger.info(f"Total collected: {len(all_posts)} posts, {len(all_comments)} comments.")

        # 3. Export Raw Data to CSV
        posts_df = pd.DataFrame(all_posts)
        comments_df = pd.DataFrame(all_comments)
        
        collector.save_to_csv(posts_df, "data/raw_posts.csv")
        collector.save_to_csv(comments_df, "data/raw_comments.csv")

        # 4. Save to SQLite database (Raw data only)
        collector.save_to_sqlite(all_posts, all_comments)

        # Update run log to successful
        db_helper.update_collection_run(
            run_id=run_id,
            status="SUCCESS",
            posts_collected=len(all_posts),
            comments_collected=len(all_comments),
            details="Pipeline completed successfully."
        )
        logger.info(f"Run ID {run_id} updated with SUCCESS status.")

        # 5. Preprocessing (In-Memory Only for NLP preparation)
        logger.info("Initializing Preprocessing Pipeline...")
        preprocessor = TextPreprocessor()

        if not posts_df.empty:
            logger.info("Preprocessing posts (Title + Body)...")
            # We create a combined column to clean
            posts_df["raw_full_text"] = posts_df["title"].fillna("") + " " + posts_df["body"].fillna("")
            preprocessed_posts = preprocessor.preprocess_dataframe(
                posts_df, text_columns="raw_full_text", target_column="clean_text"
            )
            
            # Show a preview in the console
            logger.info("--- PREPROCESSING PREVIEW (POSTS) ---")
            preview_cols = ["title", "clean_text"]
            for idx, row in preprocessed_posts[preview_cols].head(3).iterrows():
                logger.info(f"RAW TITLE: {row['title']}")
                logger.info(f"CLEANED  : {row['clean_text']}")
                logger.info("-" * 40)
                
            # Save preprocessed results to CSV for future NLP phases (not saved to SQLite as per instructions)
            preprocessor.preprocess_dataframe(
                posts_df, text_columns="raw_full_text", target_column="clean_text"
            )
            preprocessed_posts_csv = os.path.join("data", "preprocessed_posts.csv")
            preprocessor.preprocess_dataframe(
                posts_df, text_columns="raw_full_text", target_column="clean_text"
            ).to_csv(preprocessed_posts_csv, index=False, encoding="utf-8")
            logger.info(f"Saved preprocessed posts to CSV: {preprocessed_posts_csv}")

        if not comments_df.empty:
            logger.info("Preprocessing comments (Body)...")
            preprocessed_comments = preprocessor.preprocess_dataframe(
                comments_df, text_columns="body", target_column="clean_text"
            )
            
            # Show a preview in the console
            logger.info("--- PREPROCESSING PREVIEW (COMMENTS) ---")
            preview_cols = ["body", "clean_text"]
            for idx, row in preprocessed_comments[preview_cols].head(3).iterrows():
                logger.info(f"RAW BODY: {row['body']}")
                logger.info(f"CLEANED : {row['clean_text']}")
                logger.info("-" * 40)
                
            preprocessed_comments_csv = os.path.join("data", "preprocessed_comments.csv")
            preprocessed_comments.to_csv(preprocessed_comments_csv, index=False, encoding="utf-8")
            logger.info(f"Saved preprocessed comments to CSV: {preprocessed_comments_csv}")

    except Exception as e:
        logger.error(f"Pipeline execution encountered an error: {e}", exc_info=True)
        # Attempt to mark run as failed in DB
        try:
            db_helper.update_collection_run(
                run_id=run_id,
                status="FAILED",
                posts_collected=len(all_posts),
                comments_collected=len(all_comments),
                details=f"Error: {str(e)}"
            )
            logger.info(f"Run ID {run_id} updated with FAILED status.")
        except Exception as db_err:
            logger.error(f"Could not update run status in DB: {db_err}")
        raise e

if __name__ == "__main__":
    run_pipeline()
