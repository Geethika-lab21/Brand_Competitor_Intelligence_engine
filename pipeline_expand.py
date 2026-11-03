import os
import time
import datetime
import pandas as pd
from src.utils.logger import logger
from src.utils.config import config
from src.utils.database_helper import DatabaseHelper
from src.data_collection.reddit_collector import RedditCollector

def evaluate_dataset_readiness(db_helper: DatabaseHelper, reports_dir: str) -> None:
    """
    Evaluates dataset volume limits and writes readiness reports.
    If posts >= 1000 and comments >= 5000: Status = READY
    Else: Status = NOT_READY
    
    Args:
        db_helper (DatabaseHelper): Database connection wrapper.
        reports_dir (str): Destination reports directory.
    """
    try:
        with db_helper.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM posts;")
            db_posts = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM comments;")
            db_comments = cursor.fetchone()[0]
            
            # Count unique subreddits combined
            cursor.execute("""
                SELECT COUNT(DISTINCT subreddit) FROM (
                    SELECT subreddit FROM posts WHERE subreddit IS NOT NULL AND subreddit != ''
                    UNION
                    SELECT subreddit FROM comments WHERE subreddit IS NOT NULL AND subreddit != ''
                );
            """)
            db_subreddits = cursor.fetchone()[0]
            
            # Count unique authors combined
            cursor.execute("""
                SELECT COUNT(DISTINCT author) FROM (
                    SELECT author FROM posts WHERE author IS NOT NULL AND author != ''
                    UNION
                    SELECT author FROM comments WHERE author IS NOT NULL AND author != ''
                );
            """)
            db_authors = cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Error querying DB for readiness gate: {e}")
        db_posts, db_comments, db_subreddits, db_authors = 0, 0, 0, 0

    collection_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    
    if db_posts >= 1000 and db_comments >= 5000:
        status = "READY"
        md_content = f"""# Phase 3 Readiness Gate Report

**Readiness Status**: `READY`

## Dataset Size Achieved
- **Total Posts**: {db_posts}
- **Total Comments**: {db_comments}

## Coverage Statistics
- **Unique Subreddits**: {db_subreddits}
- **Unique Authors**: {db_authors}
- **Collection Date**: {collection_date}

## Recommended Next Phase
The dataset is sufficiently large and ready for Natural Language Processing (NLP). We recommend proceeding to:

- **Phase 4: Sentiment Intelligence Engine**
- **Proposed Model**: `cardiffnlp/twitter-roberta-base-sentiment-latest` (RoBERTa-based sentiment classifier optimized for social media text).
"""
    else:
        status = "NOT_READY"
        missing_posts = max(0, 1000 - db_posts)
        missing_comments = max(0, 5000 - db_comments)
        
        md_content = f"""# Phase 3 Readiness Gate Report

**Readiness Status**: `NOT_READY`

## Current Dataset Size
- **Total Posts**: {db_posts}
- **Total Comments**: {db_comments}

## Missing Volume Required
- **Missing Posts**: {missing_posts}
- **Missing Comments**: {missing_comments}

## Recommended Next Actions
1. **API Credentials Setup**: Please copy `.env.example` to `.env` and configure active `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` secrets to bypass mock data generation.
2. **Execute Expanded Collection**: Run `python pipeline_expand.py` with valid keys to perform ingestion from targeted skincare forums.
3. **Subreddit List Scoping**: Broaden search terms or targeted subreddits lists inside `src/utils/config.py` if volume counts remain under the threshold.

*Note: Sentiment analysis and topic modeling are blocked and not recommended until the database volume meets the necessary thresholds.*
"""
    
    # Export readiness_status.csv
    readiness_df = pd.DataFrame([{
        "status": status,
        "posts": db_posts,
        "comments": db_comments,
        "unique_subreddits": db_subreddits,
        "unique_authors": db_authors,
        "collection_date": collection_date
    }])
    readiness_file = os.path.join(reports_dir, "readiness_status.csv")
    readiness_df.to_csv(readiness_file, index=False)
    logger.info(f"Saved readiness status data to {readiness_file}")
    
    # Export phase3_readiness.md
    readiness_md_file = os.path.join(reports_dir, "phase3_readiness.md")
    with open(readiness_md_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"Saved phase3_readiness.md to {readiness_md_file}")

def run_expanded_pipeline() -> None:
    """
    Orchestrates the expanded Phase 3 data collection pipeline.
    Tracks performance metrics, deduplication metrics, and exports summaries and readiness gates.
    """
    logger.info("==============================================")
    logger.info("Starting Expanded Reddit Data Ingestion Pipeline")
    logger.info("==============================================")

    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    summary_file = os.path.join(reports_dir, "data_collection_summary.csv")

    db_helper = DatabaseHelper(config.database_path)
    
    # Initialize run log
    run_timestamp = datetime.datetime.utcnow().isoformat()
    run_id = db_helper.log_collection_run(
        timestamp=run_timestamp,
        status="RUNNING",
        posts_collected=0,
        comments_collected=0,
        details="Expanded ingestion started."
    )

    # Initialize metrics
    perf_metrics = {
        "posts_collected": 0,
        "comments_collected": 0,
        "brands_collected": 0,
        "subreddits_covered": 0,
        "earliest_post_date": "N/A",
        "latest_post_date": "N/A",
        "duplicate_rate": 0.0,
        "collection_success_rate": 0.0,
        "collection_start_time": datetime.datetime.utcnow().isoformat(),
        "collection_end_time": "N/A",
        "elapsed_seconds": 0.0,
        "posts_per_minute": 0.0,
        "comments_per_minute": 0.0
    }

    start_time = time.time()
    collector = None

    try:
        # 1. Initialize RedditCollector (this will throw ValueError if secrets are missing)
        collector = RedditCollector(db_helper=db_helper, mock_mode=False)

        all_posts = []
        all_comments = []

        # Track targeted subreddits
        subreddits = config.target_subreddits
        brands = list(config.brands_search_terms.keys())

        # 2. Run Scraping Loop
        for brand in brands:
            # Fetch posts (limit 100 per query to target higher volumes)
            posts = collector.fetch_brand_posts(brand, limit_per_query=100)
            all_posts.extend(posts)
            
            # Fetch comments for each post
            for post in posts:
                comments = collector.fetch_comments(post["id"], brand, max_comments=20)
                all_comments.extend(comments)

        end_time = time.time()
        elapsed = end_time - start_time
        perf_metrics["elapsed_seconds"] = round(elapsed, 2)
        perf_metrics["collection_end_time"] = datetime.datetime.utcnow().isoformat()

        # Deduplicate list items (in-memory deduplication comparison)
        unique_posts_count = len({p["id"] for p in all_posts})
        unique_comments_count = len({c["id"] for c in all_comments})
        
        attempted_posts = len(all_posts)
        attempted_comments = len(all_comments)
        
        duplicate_posts = attempted_posts - unique_posts_count
        duplicate_comments = attempted_comments - unique_comments_count
        
        total_attempted = attempted_posts + attempted_comments
        total_duplicates = duplicate_posts + duplicate_comments
        
        duplicate_rate = (total_duplicates / total_attempted) if total_attempted > 0 else 0.0
        perf_metrics["duplicate_rate"] = round(duplicate_rate, 4)

        # 3. SQLite Ingestion & raw CSV saves
        if all_posts:
            posts_df = pd.DataFrame(all_posts)
            comments_df = pd.DataFrame(all_comments) if all_comments else pd.DataFrame()
            
            # Export raw CSV backups
            collector.save_to_csv(posts_df, "data/raw_posts.csv")
            if not comments_df.empty:
                collector.save_to_csv(comments_df, "data/raw_comments.csv")
                
            # Write to database
            collector.save_to_sqlite(all_posts, all_comments)

            # Get timestamp ranges
            created_times = [p["created_utc"] for p in all_posts if p.get("created_utc")]
            if created_times:
                perf_metrics["earliest_post_date"] = datetime.datetime.utcfromtimestamp(min(created_times)).isoformat()
                perf_metrics["latest_post_date"] = datetime.datetime.utcfromtimestamp(max(created_times)).isoformat()

        # Calculate counts
        perf_metrics["posts_collected"] = unique_posts_count
        perf_metrics["comments_collected"] = unique_comments_count
        perf_metrics["brands_collected"] = len(brands)
        perf_metrics["subreddits_covered"] = len(subreddits)
        
        # Calculate rates
        elapsed_min = elapsed / 60.0 if elapsed > 0 else 1.0
        perf_metrics["posts_per_minute"] = round(unique_posts_count / elapsed_min, 2)
        perf_metrics["comments_per_minute"] = round(unique_comments_count / elapsed_min, 2)
        perf_metrics["collection_success_rate"] = 1.0

        # Save collection summary CSV
        summary_df = pd.DataFrame([perf_metrics])
        summary_df.to_csv(summary_file, index=False)
        logger.info(f"Saved collection summary metrics to {summary_file}")

        # Update run database log
        db_helper.update_collection_run(
            run_id=run_id,
            status="SUCCESS",
            posts_collected=unique_posts_count,
            comments_collected=unique_comments_count,
            details=f"Live collection completed in {round(elapsed, 2)} seconds."
        )
        
        # Automatically evaluate dataset readiness at the end of successful run
        evaluate_dataset_readiness(db_helper, reports_dir)
        logger.info("Expanded collection completed successfully.")

    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        perf_metrics["elapsed_seconds"] = round(elapsed, 2)
        perf_metrics["collection_end_time"] = datetime.datetime.utcnow().isoformat()
        perf_metrics["collection_success_rate"] = 0.0

        # Write error summary CSV
        summary_df = pd.DataFrame([perf_metrics])
        summary_df.to_csv(summary_file, index=False)
        logger.error(f"Expanded collection failed: {e}", exc_info=True)
        
        # Update run database log with error
        try:
            db_helper.update_collection_run(
                run_id=run_id,
                status="FAILED",
                posts_collected=0,
                comments_collected=0,
                details=f"Failure: {str(e)}"
            )
        except Exception as db_err:
            logger.error(f"Could not update failed run log in DB: {db_err}")
            
        # Automatically evaluate dataset readiness during failures to reflect current state
        evaluate_dataset_readiness(db_helper, reports_dir)
        
        # Reraise exception so that the run fails as required
        raise e

if __name__ == "__main__":
    run_expanded_pipeline()
