import os
import sqlite3
from typing import Dict, List, Optional, Any
from src.utils.logger import logger

class DatabaseHelper:
    """
    SQLite Helper for the Brand & Competitor Intelligence Engine.
    Handles schema initialization, foreign keys enforcement, and bulk upsert operations.
    """

    def __init__(self, db_path: str) -> None:
        """
        Initializes the Database Helper.
        
        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
        # Ensure the directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """
        Establishes a connection to the SQLite database with foreign keys enabled.
        
        Returns:
            sqlite3.Connection: Database connection object.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign key constraint support in SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """
        Initializes the database schema if tables do not exist.
        """
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                brand_id INTEGER NOT NULL,
                title TEXT,
                body TEXT,
                subreddit TEXT,
                score INTEGER,
                author TEXT,
                created_utc REAL,
                source TEXT NOT NULL,
                rating REAL,
                FOREIGN KEY (brand_id) REFERENCES brands (id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                brand_id INTEGER NOT NULL,
                body TEXT NOT NULL,
                subreddit TEXT,
                score INTEGER,
                author TEXT,
                created_utc REAL,
                source TEXT NOT NULL,
                rating REAL,
                FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
                FOREIGN KEY (brand_id) REFERENCES brands (id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS collection_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                posts_collected INTEGER NOT NULL,
                comments_collected INTEGER NOT NULL,
                details TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sentiment_predictions (
                source_record_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                brand TEXT NOT NULL,
                sentiment_label TEXT NOT NULL,
                sentiment_score REAL NOT NULL,
                sentiment_confidence REAL NOT NULL,
                prediction_timestamp TEXT NOT NULL
            );
            """
        ]

        logger.info("Initializing SQLite database and tables if not exist...")
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for query in schema_queries:
                    cursor.execute(query)
                conn.commit()
            logger.info("Database initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error initializing SQLite database: {e}", exc_info=True)
            raise e

    def insert_brands(self, brand_names: List[str]) -> Dict[str, int]:
        """
        Inserts brands into the database if they do not exist and returns a brand-to-ID mapping.
        
        Args:
            brand_names (List[str]): List of brand names to ensure exist.
            
        Returns:
            Dict[str, int]: Mapping of brand name to its database ID.
        """
        brand_map: Dict[str, int] = {}
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for name in brand_names:
                    cursor.execute(
                        "INSERT OR IGNORE INTO brands (name) VALUES (?);", (name,)
                    )
                conn.commit()
                
                # Fetch mapping
                cursor.execute("SELECT id, name FROM brands;")
                rows = cursor.fetchall()
                for row in rows:
                    brand_map[row["name"]] = row["id"]
        except sqlite3.Error as e:
            logger.error(f"Error inserting/fetching brands: {e}", exc_info=True)
            raise e
        return brand_map

    def upsert_posts(self, posts: List[Dict[str, Any]]) -> None:
        """
        Performs bulk upsert of posts. If a post with the same id exists, it will be updated.
        
        Args:
            posts (List[Dict[str, Any]]): List of post dictionaries.
        """
        if not posts:
            return

        query = """
        INSERT INTO posts (id, brand_id, title, body, subreddit, score, author, created_utc, source, rating)
        VALUES (:id, :brand_id, :title, :body, :subreddit, :score, :author, :created_utc, :source, :rating)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            body = excluded.body,
            subreddit = excluded.subreddit,
            score = excluded.score,
            author = excluded.author,
            created_utc = excluded.created_utc,
            source = excluded.source,
            rating = excluded.rating;
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, posts)
                conn.commit()
            logger.info(f"Successfully upserted {len(posts)} posts into SQLite.")
        except sqlite3.Error as e:
            logger.error(f"Error upserting posts: {e}", exc_info=True)
            raise e

    def upsert_comments(self, comments: List[Dict[str, Any]]) -> None:
        """
        Performs bulk upsert of comments. If a comment with the same id exists, it will be updated.
        
        Args:
            comments (List[Dict[str, Any]]): List of comment dictionaries.
        """
        if not comments:
            return

        query = """
        INSERT INTO comments (id, post_id, brand_id, body, subreddit, score, author, created_utc, source, rating)
        VALUES (:id, :post_id, :brand_id, :body, :subreddit, :score, :author, :created_utc, :source, :rating)
        ON CONFLICT(id) DO UPDATE SET
            post_id = excluded.post_id,
            brand_id = excluded.brand_id,
            body = excluded.body,
            subreddit = excluded.subreddit,
            score = excluded.score,
            author = excluded.author,
            created_utc = excluded.created_utc,
            source = excluded.source,
            rating = excluded.rating;
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, comments)
                conn.commit()
            logger.info(f"Successfully upserted {len(comments)} comments into SQLite.")
        except sqlite3.Error as e:
            logger.error(f"Error upserting comments: {e}", exc_info=True)
            raise e

    def log_collection_run(
        self, timestamp: str, status: str, posts_collected: int, comments_collected: int, details: Optional[str] = None
    ) -> int:
        """
        Logs a new pipeline execution run to the collection_runs table.
        
        Args:
            timestamp (str): ISO 8601 string of run time.
            status (str): Current status ('RUNNING', 'SUCCESS', 'FAILED').
            posts_collected (int): Count of posts collected.
            comments_collected (int): Count of comments collected.
            details (Optional[str]): Optional details or errors.
            
        Returns:
            int: The primary key ID of the logged run.
        """
        query = """
        INSERT INTO collection_runs (timestamp, status, posts_collected, comments_collected, details)
        VALUES (?, ?, ?, ?, ?);
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (timestamp, status, posts_collected, comments_collected, details))
                conn.commit()
                run_id = cursor.lastrowid
                return run_id if run_id is not None else -1
        except sqlite3.Error as e:
            logger.error(f"Error logging collection run: {e}", exc_info=True)
            return -1

    def update_collection_run(
        self, run_id: int, status: str, posts_collected: int, comments_collected: int, details: Optional[str] = None
    ) -> None:
        """
        Updates an existing pipeline execution run entry.
        
        Args:
            run_id (int): Database ID of the run.
            status (str): Updated status ('SUCCESS', 'FAILED').
            posts_collected (int): Total count of posts collected.
            comments_collected (int): Total count of comments collected.
            details (Optional[str]): Final details or error message.
        """
        query = """
        UPDATE collection_runs
        SET status = ?, posts_collected = ?, comments_collected = ?, details = ?
        WHERE id = ?;
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (status, posts_collected, comments_collected, details, run_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error updating collection run {run_id}: {e}", exc_info=True)

    def upsert_sentiment_predictions(self, predictions: List[Dict[str, Any]]) -> None:
        """
        Performs bulk upsert of sentiment predictions into SQLite.
        
        Args:
            predictions (List[Dict[str, Any]]): List of prediction dictionaries.
        """
        if not predictions:
            return

        query = """
        INSERT INTO sentiment_predictions (source_record_id, source, brand, sentiment_label, sentiment_score, sentiment_confidence, prediction_timestamp)
        VALUES (:source_record_id, :source, :brand, :sentiment_label, :sentiment_score, :sentiment_confidence, :prediction_timestamp)
        ON CONFLICT(source_record_id) DO UPDATE SET
            source = excluded.source,
            brand = excluded.brand,
            sentiment_label = excluded.sentiment_label,
            sentiment_score = excluded.sentiment_score,
            sentiment_confidence = excluded.sentiment_confidence,
            prediction_timestamp = excluded.prediction_timestamp;
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, predictions)
                conn.commit()
            logger.info(f"Successfully upserted {len(predictions)} sentiment predictions into SQLite.")
        except sqlite3.Error as e:
            logger.error(f"Error upserting sentiment predictions: {e}", exc_info=True)
            raise e
