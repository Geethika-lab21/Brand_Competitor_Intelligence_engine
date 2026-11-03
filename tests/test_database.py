import sqlite3
import pytest
from src.utils.database_helper import DatabaseHelper

@pytest.fixture
def db_helper(tmp_path) -> DatabaseHelper:
    # Use a temporary file-based database for unit testing
    db_file = tmp_path / "test_brand_intelligence.db"
    return DatabaseHelper(str(db_file))

def test_database_initialization(db_helper: DatabaseHelper) -> None:
    conn = db_helper.get_connection()
    cursor = conn.cursor()
    
    # Check that tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    
    assert "brands" in tables
    assert "posts" in tables
    assert "comments" in tables
    assert "collection_runs" in tables
    conn.close()

def test_insert_brands(db_helper: DatabaseHelper) -> None:
    brands = ["Mamaearth", "Minimalist"]
    brand_map = db_helper.insert_brands(brands)
    
    assert "Mamaearth" in brand_map
    assert "Minimalist" in brand_map
    assert isinstance(brand_map["Mamaearth"], int)
    
    # Verify duplicates are ignored and same IDs are returned
    brand_map_dup = db_helper.insert_brands(["Mamaearth", "Minimalist", "The Ordinary"])
    assert brand_map_dup["Mamaearth"] == brand_map["Mamaearth"]
    assert "The Ordinary" in brand_map_dup

def test_upsert_posts(db_helper: DatabaseHelper) -> None:
    brand_map = db_helper.insert_brands(["Mamaearth"])
    brand_id = brand_map["Mamaearth"]
    
    posts = [
        {
            "id": "post1",
            "brand_id": brand_id,
            "title": "Mamaearth Review",
            "body": "Good product.",
            "subreddit": "IndianSkincareAddicts",
            "score": 10,
            "author": "user1",
            "created_utc": 1680000000.0,
            "source": "reddit",
            "rating": None
        }
    ]
    
    # Perform upsert
    db_helper.upsert_posts(posts)
    
    # Verify insertion
    conn = db_helper.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id='post1';")
    row = cursor.fetchone()
    assert row is not None
    assert row["title"] == "Mamaearth Review"
    assert row["score"] == 10
    
    # Modify post and upsert again to check update behavior
    posts[0]["title"] = "Mamaearth Updated Review"
    posts[0]["score"] = 25
    db_helper.upsert_posts(posts)
    
    cursor.execute("SELECT * FROM posts WHERE id='post1';")
    row = cursor.fetchone()
    assert row is not None
    assert row["title"] == "Mamaearth Updated Review"
    assert row["score"] == 25
    conn.close()

def test_upsert_comments(db_helper: DatabaseHelper) -> None:
    brand_map = db_helper.insert_brands(["Mamaearth"])
    brand_id = brand_map["Mamaearth"]
    
    # Insert parent post first due to FK constraints
    posts = [
        {
            "id": "post1",
            "brand_id": brand_id,
            "title": "Mamaearth Review",
            "body": "Good product.",
            "subreddit": "IndianSkincareAddicts",
            "score": 10,
            "author": "user1",
            "created_utc": 1680000000.0,
            "source": "reddit",
            "rating": None
        }
    ]
    db_helper.upsert_posts(posts)
    
    comments = [
        {
            "id": "comm1",
            "post_id": "post1",
            "brand_id": brand_id,
            "body": "I agree!",
            "subreddit": "IndianSkincareAddicts",
            "score": 5,
            "author": "user2",
            "created_utc": 1680000100.0,
            "source": "reddit",
            "rating": None
        }
    ]
    
    db_helper.upsert_comments(comments)
    
    # Verify insertion
    conn = db_helper.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM comments WHERE id='comm1';")
    row = cursor.fetchone()
    assert row is not None
    assert row["body"] == "I agree!"
    
    # Test update comment
    comments[0]["body"] = "Actually, I changed my mind."
    db_helper.upsert_comments(comments)
    cursor.execute("SELECT * FROM comments WHERE id='comm1';")
    row = cursor.fetchone()
    assert row["body"] == "Actually, I changed my mind."
    conn.close()

def test_foreign_key_constraints(db_helper: DatabaseHelper) -> None:
    # Attempting to insert a post with a non-existent brand_id should fail
    # Brand ID 999 does not exist
    post = {
        "id": "post_fail",
        "brand_id": 999,
        "title": "Failure post",
        "body": "No brand exists",
        "subreddit": "skincare",
        "score": 0,
        "author": "nobody",
        "created_utc": 1680000000.0,
        "source": "reddit",
        "rating": None
    }
    
    with pytest.raises(sqlite3.IntegrityError):
        db_helper.upsert_posts([post])

def test_collection_runs(db_helper: DatabaseHelper) -> None:
    run_id = db_helper.log_collection_run(
        timestamp="2026-06-10T12:00:00",
        status="RUNNING",
        posts_collected=0,
        comments_collected=0,
        details="Starting..."
    )
    
    assert run_id > 0
    
    conn = db_helper.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM collection_runs WHERE id=?;", (run_id,))
    row = cursor.fetchone()
    assert row["status"] == "RUNNING"
    assert row["posts_collected"] == 0
    
    # Update run
    db_helper.update_collection_run(
        run_id=run_id,
        status="SUCCESS",
        posts_collected=15,
        comments_collected=45,
        details="Done!"
    )
    
    cursor.execute("SELECT * FROM collection_runs WHERE id=?;", (run_id,))
    row = cursor.fetchone()
    assert row["status"] == "SUCCESS"
    assert row["posts_collected"] == 15
    assert row["comments_collected"] == 45
    assert row["details"] == "Done!"
    conn.close()
