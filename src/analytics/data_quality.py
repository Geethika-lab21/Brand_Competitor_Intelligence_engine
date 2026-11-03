import os
from typing import Dict, Any, Tuple
import pandas as pd
from src.utils.logger import logger
from src.utils.database_helper import DatabaseHelper

class DataQualityAnalyzer:
    """
    Analyzes and reports the quality of the raw ingestion dataset in SQLite.
    Computes metrics such as completeness, null columns, duplicate records,
    and descriptive distributions.
    """

    def __init__(self, db_helper: DatabaseHelper) -> None:
        """
        Initializes the analyzer with a database helper to retrieve raw tables.
        
        Args:
            db_helper (DatabaseHelper): Database connection wrapper.
        """
        self.db_helper = db_helper
        self.posts_df, self.comments_df, self.brands_df = self._load_data()

    def _load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Loads raw tables from SQLite into Pandas DataFrames.
        """
        try:
            with self.db_helper.get_connection() as conn:
                posts = pd.read_sql_query("SELECT * FROM posts;", conn)
                comments = pd.read_sql_query("SELECT * FROM comments;", conn)
                brands = pd.read_sql_query("SELECT * FROM brands;", conn)
            logger.info(f"Loaded database tables for quality checks: {len(posts)} posts, {len(comments)} comments.")
            return posts, comments, brands
        except Exception as e:
            logger.error(f"Error loading tables for data quality: {e}", exc_info=True)
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def compute_quality_metrics(self) -> Dict[str, Any]:
        """
        Computes structured data quality statistics for posts and comments.
        
        Returns:
            Dict[str, Any]: Nested metrics dictionary.
        """
        if self.posts_df.empty and self.comments_df.empty:
            logger.warning("DataFrames are empty. Cannot compute metrics.")
            return {}

        # 1. Row counts
        total_posts = len(self.posts_df)
        total_comments = len(self.comments_df)
        total_brands = len(self.brands_df)

        # 2. Score averages
        avg_post_score = float(self.posts_df["score"].mean()) if total_posts > 0 else 0.0
        avg_comment_score = float(self.comments_df["score"].mean()) if total_comments > 0 else 0.0

        # 3. Unique entities
        post_authors = set(self.posts_df["author"].dropna().unique()) if total_posts > 0 else set()
        comment_authors = set(self.comments_df["author"].dropna().unique()) if total_comments > 0 else set()
        unique_authors = len(post_authors.union(comment_authors))

        post_subreddits = set(self.posts_df["subreddit"].dropna().unique()) if total_posts > 0 else set()
        comment_subreddits = set(self.comments_df["subreddit"].dropna().unique()) if total_comments > 0 else set()
        unique_subreddits = len(post_subreddits.union(comment_subreddits))

        # 4. Duplicate counts
        # We check duplicates based on primary key 'id'
        dup_posts = int(self.posts_df["id"].duplicated().sum()) if total_posts > 0 else 0
        dup_comments = int(self.comments_df["id"].duplicated().sum()) if total_comments > 0 else 0

        # 5. Missing values per column
        missing_posts = self.posts_df.isnull().sum().to_dict() if total_posts > 0 else {}
        missing_comments = self.comments_df.isnull().sum().to_dict() if total_comments > 0 else {}

        metrics = {
            "summary": {
                "total_posts": total_posts,
                "total_comments": total_comments,
                "total_brands": total_brands,
                "unique_authors": unique_authors,
                "unique_subreddits": unique_subreddits,
                "avg_post_score": round(avg_post_score, 2),
                "avg_comment_score": round(avg_comment_score, 2),
                "duplicate_posts": dup_posts,
                "duplicate_comments": dup_comments
            },
            "missing_values": {
                "posts": missing_posts,
                "comments": missing_comments
            }
        }
        return metrics

    def export_csv_report(self, metrics: Dict[str, Any], file_path: str) -> None:
        """
        Exports the computed summary metrics to a flat CSV file.
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            summary_data = metrics.get("summary", {})
            df = pd.DataFrame(list(summary_data.items()), columns=["metric", "value"])
            df.to_csv(file_path, index=False, encoding="utf-8")
            logger.info(f"Saved CSV Data Quality Report to: {file_path}")
        except Exception as e:
            logger.error(f"Failed to export Data Quality CSV: {e}", exc_info=True)

    def export_markdown_report(self, metrics: Dict[str, Any], file_path: str) -> None:
        """
        Exports a formatted Markdown Data Quality report.
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            summary = metrics.get("summary", {})
            missing = metrics.get("missing_values", {})
            
            md_content = f"""# Data Quality Report

Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. Dataset Overview

| Metric | Value |
| :--- | :--- |
| **Total Posts Collected** | {summary.get('total_posts')} |
| **Total Comments Collected** | {summary.get('total_comments')} |
| **Total Brands Monitored** | {summary.get('total_brands')} |
| **Unique Discussion Authors** | {summary.get('unique_authors')} |
| **Unique Subreddits Covered** | {summary.get('unique_subreddits')} |
| **Average Post Score (Upvotes)** | {summary.get('avg_post_score')} |
| **Average Comment Score** | {summary.get('avg_comment_score')} |
| **Duplicate Post Records** | {summary.get('duplicate_posts')} |
| **Duplicate Comment Records** | {summary.get('duplicate_comments')} |

## 2. Missing Values Analysis

### Posts Table Completeness
| Column | Missing Count | Null Percentage |
| :--- | :--- | :--- |
"""
            total_p = summary.get('total_posts', 1) or 1
            for col, count in missing.get("posts", {}).items():
                pct = (count / total_p) * 100
                md_content += f"| `{col}` | {count} | {pct:.2f}% |\n"

            md_content += """
### Comments Table Completeness
| Column | Missing Count | Null Percentage |
| :--- | :--- | :--- |
"""
            total_c = summary.get('total_comments', 1) or 1
            for col, count in missing.get("comments", {}).items():
                pct = (count / total_c) * 100
                md_content += f"| `{col}` | {count} | {pct:.2f}% |\n"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            logger.info(f"Saved Markdown Data Quality Report to: {file_path}")
        except Exception as e:
            logger.error(f"Failed to export Data Quality Markdown: {e}", exc_info=True)

    def print_console_summary(self, metrics: Dict[str, Any]) -> None:
        """
        Prints a neat text summary of data quality metrics to the console.
        """
        summary = metrics.get("summary", {})
        print("\n" + "=" * 50)
        print("           DATA QUALITY REPORT SUMMARY           ")
        print("=" * 50)
        print(f"Total Posts:         {summary.get('total_posts')}")
        print(f"Total Comments:      {summary.get('total_comments')}")
        print(f"Total Brands:        {summary.get('total_brands')}")
        print(f"Unique Authors:      {summary.get('unique_authors')}")
        print(f"Unique Subreddits:   {summary.get('unique_subreddits')}")
        print(f"Avg Post Score:      {summary.get('avg_post_score')}")
        print(f"Avg Comment Score:   {summary.get('avg_comment_score')}")
        print(f"Duplicate Posts:     {summary.get('duplicate_posts')}")
        print(f"Duplicate Comments:  {summary.get('duplicate_comments')}")
        print("=" * 50 + "\n")
