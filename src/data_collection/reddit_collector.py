import os
import re
import time
from typing import List, Dict, Any, Optional
import pandas as pd
import praw
from src.utils.logger import logger
from src.utils.config import config
from src.utils.database_helper import DatabaseHelper

class RedditCollector:
    """
    Reddit Data Collection Pipeline using PRAW.
    Supports API query searches for multiple brands, targeted subreddits,
    comment extraction, diagnostics tracking, and rate-limiting detection.
    """

    def __init__(self, db_helper: Optional[DatabaseHelper] = None, mock_mode: bool = False) -> None:
        """
        Initializes the Reddit Collector.
        
        Args:
            db_helper (Optional[DatabaseHelper]): Optional DatabaseHelper for DB operations.
            mock_mode (bool): If True, runs in test mock mode. Enforces live keys at runtime if False.
        """
        self.db_helper = db_helper
        self.reddit: Optional[praw.Reddit] = None
        self.mock_mode = mock_mode
        
        # Performance & collection diagnostics registry
        self.diagnostics = {
            "queries_executed": [],
            "subreddits_searched": [],
            "posts_returned": 0,
            "comments_returned": 0,
            "api_errors": [],
            "rate_limiting_events": 0
        }
        
        if self.mock_mode:
            logger.info("Initializing RedditCollector in developmental Mock/Offline mode.")
            return

        # Enforce API credentials setup in Phase 3
        if not config.validate_reddit_creds():
            raise ValueError(
                "Reddit API credentials (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET) are missing. "
                "Silent mock-mode is disabled in Phase 3. Please configure your .env file."
            )

        try:
            self.reddit = praw.Reddit(
                client_id=config.reddit_client_id,
                client_secret=config.reddit_client_secret,
                user_agent=config.reddit_user_agent,
                username=config.reddit_username,
                password=config.reddit_password
            )
            # Verify credentials with a quick read-only check
            self.reddit.read_only = True
            list(self.reddit.subreddit("test").hot(limit=1))
            logger.info("Reddit PRAW API client initialized and authenticated successfully.")
        except Exception as e:
            err_msg = f"Reddit client authentication failed: {e}."
            logger.error(err_msg)
            raise ConnectionError(err_msg) from e

    def detect_brand_mentions(self, title: str, body: str) -> Dict[str, int]:
        """
        Detects and counts mentions of different brands in the title and body.
        
        Args:
            title (str): Post title.
            body (str): Post body.
            
        Returns:
            Dict[str, int]: Mention count per brand.
        """
        text = f"{title} {body}".lower()
        mentions = {}
        for brand, terms in config.brands_search_terms.items():
            count = 0
            for term in terms:
                count += len(re.findall(re.escape(term.lower()), text))
            mentions[brand] = count
        return mentions

    def resolve_primary_brand(self, title: str, body: str, default_brand: str) -> str:
        """
        Resolves the primary brand for a post when multiple brand names are mentioned.
        Uses mention frequency. If there is a tie, defaults to the default brand.
        
        Args:
            title (str): Post title.
            body (str): Post body.
            default_brand (str): The search brand that retrieved the post.
            
        Returns:
            str: Resolved brand name.
        """
        mentions = self.detect_brand_mentions(title, body)
        active_brands = [b for b, count in mentions.items() if count > 0]
        
        if not active_brands:
            return default_brand
        
        if len(active_brands) == 1:
            return active_brands[0]
            
        logger.info(
            f"Brand co-mention detected. Active brands: {active_brands}. "
            f"Counts: {mentions}. Text snippet: '{title[:50]}...'"
        )
        
        # Find brand with maximum mentions
        max_mentions = max(mentions.values())
        candidates = [b for b, count in mentions.items() if count == max_mentions]
        
        if len(candidates) == 1:
            return candidates[0]
        return default_brand

    def fetch_brand_posts(self, brand_name: str, limit_per_query: int = 50) -> List[Dict[str, Any]]:
        """
        Searches targeted subreddits config list for brand matching terms.
        Tracks diagnostics queries and errors.
        
        Args:
            brand_name (str): The target brand (e.g., "Mamaearth", "Minimalist").
            limit_per_query (int): Maximum number of submissions to fetch per search query.
            
        Returns:
            List[Dict[str, Any]]: List of unique post dictionaries.
        """
        search_terms = config.brands_search_terms.get(brand_name, [brand_name])
        logger.info(f"Fetching posts for brand '{brand_name}' using terms: {search_terms}")
        
        if self.mock_mode:
            posts = self._generate_mock_posts(brand_name, limit_per_query)
            self.diagnostics["posts_returned"] += len(posts)
            return posts

        assert self.reddit is not None, "Reddit client is not initialized."

        unique_posts: Dict[str, Dict[str, Any]] = {}
        
        for subreddit_name in config.target_subreddits:
            if subreddit_name not in self.diagnostics["subreddits_searched"]:
                self.diagnostics["subreddits_searched"].append(subreddit_name)
                
            for term in search_terms:
                query_str = f"subreddit:{subreddit_name} {term}"
                self.diagnostics["queries_executed"].append(query_str)
                logger.info(f"Querying: r/{subreddit_name} for '{term}'")
                
                try:
                    submissions = self.reddit.subreddit(subreddit_name).search(term, limit=limit_per_query)
                    for sub in submissions:
                        if sub.id in unique_posts:
                            continue
                        
                        # Disambiguate multi-brand mentions
                        resolved_brand = self.resolve_primary_brand(sub.title, sub.selftext, brand_name)
                        
                        author_name = sub.author.name if sub.author else "[deleted]"
                        unique_posts[sub.id] = {
                            "id": sub.id,
                            "brand_name": resolved_brand,
                            "title": sub.title,
                            "body": sub.selftext,
                            "subreddit": sub.subreddit.display_name,
                            "score": sub.score,
                            "author": author_name,
                            "created_utc": sub.created_utc,
                            "source": "reddit",
                            "rating": None
                        }
                except Exception as e:
                    err_msg = f"API Error searching term '{term}' in r/{subreddit_name}: {e}"
                    logger.error(err_msg, exc_info=True)
                    self.diagnostics["api_errors"].append(err_msg)
                    if "ratelimit" in str(e).lower() or "429" in str(e):
                        self.diagnostics["rate_limiting_events"] += 1
                        # Backoff if we hit rate limit
                        time.sleep(5)
                        
        self.diagnostics["posts_returned"] += len(unique_posts)
        return list(unique_posts.values())

    def fetch_comments(self, post_id: str, brand_name: str, max_comments: int = 20) -> List[Dict[str, Any]]:
        """
        Fetches comments for a specific post.
        Tracks diagnostics comments returned and failures.
        
        Args:
            post_id (str): Reddit submission ID.
            brand_name (str): Target brand name.
            max_comments (int): Max comments to extract.
            
        Returns:
            List[Dict[str, Any]]: List of comment dictionaries.
        """
        logger.debug(f"Fetching comments for post ID '{post_id}'...")
        
        if self.mock_mode:
            comments = self._generate_mock_comments(post_id, brand_name, max_comments)
            self.diagnostics["comments_returned"] += len(comments)
            return comments

        assert self.reddit is not None, "Reddit client is not initialized."

        comment_dicts: List[Dict[str, Any]] = []
        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)
            comments = submission.comments.list()
            
            for comment in comments[:max_comments]:
                author_name = comment.author.name if comment.author else "[deleted]"
                comment_dicts.append({
                    "id": comment.id,
                    "post_id": post_id,
                    "brand_id": 0,  # Will be mapped during DB write
                    "brand_name": brand_name,
                    "body": comment.body,
                    "subreddit": comment.subreddit.display_name if hasattr(comment, "subreddit") else None,
                    "score": comment.score,
                    "author": author_name,
                    "created_utc": comment.created_utc,
                    "source": "reddit",
                    "rating": None
                })
        except Exception as e:
            err_msg = f"API Error fetching comments for post '{post_id}': {e}"
            logger.error(err_msg, exc_info=True)
            self.diagnostics["api_errors"].append(err_msg)
            if "ratelimit" in str(e).lower() or "429" in str(e):
                self.diagnostics["rate_limiting_events"] += 1
            
        self.diagnostics["comments_returned"] += len(comment_dicts)
        return comment_dicts

    def save_to_csv(self, df: pd.DataFrame, file_path: str) -> None:
        """
        Saves a DataFrame to a CSV file.
        """
        try:
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            df.to_csv(file_path, index=False, encoding="utf-8")
            logger.info(f"Successfully saved {len(df)} records to CSV: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save CSV to {file_path}: {e}", exc_info=True)

    def save_to_sqlite(self, posts: List[Dict[str, Any]], comments: List[Dict[str, Any]]) -> None:
        """
        Saves posts and comments to the SQLite database via the database helper.
        """
        if not self.db_helper:
            logger.warning("DatabaseHelper is not configured. Skipping SQLite ingestion.")
            return

        try:
            unique_brands = list(set([p["brand_name"] for p in posts] + [c["brand_name"] for c in comments]))
            if not unique_brands:
                unique_brands = ["Mamaearth", "Minimalist"]
            
            brand_map = self.db_helper.insert_brands(unique_brands)
            
            db_posts = []
            for p in posts:
                post_copy = p.copy()
                b_name = post_copy.pop("brand_name")
                post_copy["brand_id"] = brand_map.get(b_name, 1)
                db_posts.append(post_copy)
                
            db_comments = []
            for c in comments:
                comment_copy = c.copy()
                b_name = comment_copy.pop("brand_name")
                comment_copy["brand_id"] = brand_map.get(b_name, 1)
                db_comments.append(comment_copy)

            self.db_helper.upsert_posts(db_posts)
            self.db_helper.upsert_comments(db_comments)
            
        except Exception as e:
            logger.error(f"SQLite ingestion failed: {e}", exc_info=True)
            raise e

    # --- Offline / Mock Data Generators ---
    
    def _generate_mock_posts(self, brand_name: str, limit: int) -> List[Dict[str, Any]]:
        """
        Generates realistic mock Reddit posts.
        """
        logger.info(f"Generating mock posts for {brand_name}...")
        now = time.time()
        mock_data = {
            "Mamaearth": [
                {
                    "title": "Mamaearth onion shampoo is causing extreme hair fall",
                    "body": "I have been using Mamaearth Onion Shampoo for 2 weeks and my hair is falling out in clumps. Anyone else experiencing this?",
                    "subreddit": "IndianSkincareAddicts",
                    "score": 42
                },
                {
                    "title": "Is Mamaearth moisturizer safe for oily sensitive skin?",
                    "body": "I want to buy the Vitamin C oil-free moisturizer. Is it actually good or just marketing hype?",
                    "subreddit": "SkincareAddiction",
                    "score": 15
                },
                {
                    "title": "Why does Mamaearth have so many reviews online but poor reputation here?",
                    "body": "On Nykaa and Amazon, Mamaearth has 4.5+ stars, but on reddit everyone hates it. Why the disparity?",
                    "subreddit": "IndianSkincareAddicts",
                    "score": 120
                }
            ],
            "Minimalist": [
                {
                    "title": "Minimalist 10% Niacinamide serum is a total game changer",
                    "body": "I've struggled with acne scars for years. Minimalist Niacinamide cleared them up in a month. Highly recommend!",
                    "subreddit": "IndianSkincareAddicts",
                    "score": 85
                },
                {
                    "title": "Minimalist sunscreen SPF 50 review: white cast issues",
                    "body": "It claims to have no white cast, but it makes me look like a ghost and feels super greasy. Returning it.",
                    "subreddit": "SkincareAddiction",
                    "score": 28
                },
                {
                    "title": "Minimalist vs The Ordinary - which brand is better for serums?",
                    "body": "Minimalist is cheaper in India, but is the quality comparable to TO? Let me know your thoughts.",
                    "subreddit": "IndianSkincareAddicts",
                    "score": 67
                }
            ]
        }
        
        co_mention_posts = [
            {
                "title": "Comparison: Mamaearth Vitamin C vs Minimalist Vitamin C",
                "body": "Looking to add Vitamin C to my routine. Mamaearth is cheaper, but Minimalist lists ingredients percentages. Which one works better for hyperpigmentation?",
                "subreddit": "IndianSkincareAddicts",
                "score": 55
            }
        ]
        
        source_posts = mock_data.get(brand_name, [])
        if brand_name == "Minimalist":
            source_posts = source_posts + co_mention_posts
            
        posts = []
        for i, p in enumerate(source_posts[:limit]):
            post_id = f"mock_post_{brand_name.lower()}_{i}"
            resolved_brand = self.resolve_primary_brand(p["title"], p["body"], brand_name)
            posts.append({
                "id": post_id,
                "brand_name": resolved_brand,
                "title": p["title"],
                "body": p["body"],
                "subreddit": p["subreddit"],
                "score": p["score"],
                "author": f"skin_enthusiast_{i}",
                "created_utc": now - (i * 3600),
                "source": "reddit",
                "rating": None
            })
        return posts

    def _generate_mock_comments(self, post_id: str, brand_name: str, limit: int) -> List[Dict[str, Any]]:
        """
        Generates realistic mock Reddit comments.
        """
        now = time.time()
        comments = []
        mock_comments_pool = [
            "Totally agree! Their marketing is super aggressive but products are subpar.",
            "I had the exact same experience. Had to visit a dermatologist after using it.",
            "Honestly, it worked fine for me. Maybe it depends on skin type?",
            "Minimalist is so much better because they are transparent about formulations.",
            "The formulation is really sticky, but it does the job.",
            "Skip it and buy pharmacy products instead, much safer and cheaper!"
        ]
        
        for i in range(min(limit, len(mock_comments_pool))):
            comments.append({
                "id": f"mock_comm_{post_id}_{i}",
                "post_id": post_id,
                "brand_name": brand_name,
                "body": mock_comments_pool[i],
                "subreddit": "IndianSkincareAddicts",
                "score": i * 4 + 2,
                "author": f"reply_user_{i}",
                "created_utc": now - (i * 600),
                "source": "reddit",
                "rating": None
            })
        return comments
