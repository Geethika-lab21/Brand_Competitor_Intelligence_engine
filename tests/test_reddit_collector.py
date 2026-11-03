import pytest
from src.data_collection.reddit_collector import RedditCollector
from src.utils.config import config

def test_collector_raises_error_without_creds(monkeypatch) -> None:
    # Clear environment variables to simulate missing credentials
    monkeypatch.setattr(config, "reddit_client_id", "")
    monkeypatch.setattr(config, "reddit_client_secret", "")
    
    with pytest.raises(ValueError) as excinfo:
        # Should raise ValueError since mock_mode=False by default
        RedditCollector(mock_mode=False)
        
    assert "Reddit API credentials" in str(excinfo.value)

def test_collector_mock_initialization() -> None:
    # Under mock_mode=True, collector should initialize without throwing errors
    collector = RedditCollector(mock_mode=True)
    assert collector.mock_mode is True
    assert collector.reddit is None
    assert collector.diagnostics["posts_returned"] == 0

def test_collector_mock_data_collection_diagnostics() -> None:
    collector = RedditCollector(mock_mode=True)
    
    posts = collector.fetch_brand_posts("Mamaearth", limit_per_query=5)
    # Check mock posts size
    assert len(posts) > 0
    assert collector.diagnostics["posts_returned"] == len(posts)
    
    comments = collector.fetch_comments("mock_post_id", "Mamaearth", max_comments=3)
    assert len(comments) > 0
    assert collector.diagnostics["comments_returned"] == len(comments)

def test_brand_co_mention_resolution() -> None:
    collector = RedditCollector(mock_mode=True)
    
    # 1. Test single brand Mamaearth mention
    b1 = collector.resolve_primary_brand(
        title="I love Mamaearth shampoo", 
        body="It works really well for my dry hair", 
        default_brand="Mamaearth"
    )
    assert b1 == "Mamaearth"
    
    # 2. Test co-mention with dominant count
    b2 = collector.resolve_primary_brand(
        title="Mamaearth vs Minimalist", 
        body="I tried Minimalist niacinamide serum and Minimalist peeling solution, and they are much better than Mamaearth.",
        default_brand="Mamaearth"
    )
    # Minimalist mentioned twice, Mamaearth mentioned twice (one in title, one in body)
    # Let's check counts: "mamaearth" -> 2 mentions. "minimalist" -> 3 mentions.
    # So Minimalist wins!
    assert b2 == "Minimalist"
