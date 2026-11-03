from typing import List, Dict, Any, Optional
from src.data_sources.base_source import BaseSource
from src.data_collection.reddit_collector import RedditCollector
from src.utils.database_helper import DatabaseHelper
from src.utils.logger import logger

class RedditSource(BaseSource):
    """
    Reddit Data Source implementing the BaseSource interface.
    Scrapes and reformats Reddit posts and comments into a source-agnostic schema.
    """

    def __init__(self, db_helper: Optional[DatabaseHelper] = None) -> None:
        """
        Initializes the Reddit Source. Catches credentials failure to allow offline runs.
        """
        self.db_helper = db_helper
        self.collector: Optional[RedditCollector] = None
        self.available = False
        
        try:
            self.collector = RedditCollector(db_helper=self.db_helper, mock_mode=False)
            self.available = True
            logger.info("RedditSource initialized successfully and is available.")
        except Exception as e:
            logger.warning(
                f"Reddit client credentials missing or validation failed. "
                f"RedditSource will be unavailable: {e}"
            )

    def fetch_data(self, brand_name: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrapes posts and comments for a brand and maps them to the standardized schema.
        """
        if not self.available or not self.collector:
            logger.warning(f"RedditSource is unavailable. Skipping fetch for {brand_name}.")
            return []

        limit_per_query = kwargs.get("limit_per_query", 50)
        max_comments = kwargs.get("max_comments", 20)

        logger.info(f"RedditSource fetching data for brand '{brand_name}'...")
        posts = self.collector.fetch_brand_posts(brand_name, limit_per_query=limit_per_query)
        
        standardized_records = []
        
        for post in posts:
            # 1. Map submission (post)
            standardized_records.append({
                "source": "reddit",
                "source_record_id": post["id"],
                "brand": brand_name,
                "title": post["title"],
                "text": post["body"] if isinstance(post["body"], str) else "",
                "rating": None,  # Reddit posts do not have star ratings
                "author": post["author"],
                "created_at": post["created_utc"],
                "metadata": {
                    "subreddit": post["subreddit"],
                    "score": post["score"],
                    "record_type": "post"
                }
            })

            # 2. Map replies (comments)
            comments = self.collector.fetch_comments(post["id"], brand_name, max_comments=max_comments)
            for comment in comments:
                standardized_records.append({
                    "source": "reddit",
                    "source_record_id": comment["id"],
                    "brand": brand_name,
                    "title": None,
                    "text": comment["body"] if isinstance(comment["body"], str) else "",
                    "rating": None,
                    "author": comment["author"],
                    "created_at": comment["created_utc"],
                    "metadata": {
                        "subreddit": comment["subreddit"],
                        "score": comment["score"],
                        "parent_post_id": post["id"],
                        "record_type": "comment"
                    }
                })

        logger.info(f"RedditSource retrieved {len(standardized_records)} total records for {brand_name}.")
        return standardized_records
