import os
from typing import Dict, List
from dotenv import load_dotenv
from src.utils.logger import logger

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """
    Configuration Manager for Brand & Competitor Intelligence Engine.
    Loads and validates environment variables.
    """
    
    def __init__(self) -> None:
        # PRAW credentials
        self.reddit_client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
        self.reddit_client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
        self.reddit_user_agent: str = os.getenv("REDDIT_USER_AGENT", "brand-intel-engine/1.0")
        self.reddit_username: str = os.getenv("REDDIT_USERNAME", "")
        self.reddit_password: str = os.getenv("REDDIT_PASSWORD", "")
        
        # Database Path
        self.database_path: str = os.getenv("DATABASE_PATH", "database/brand_intelligence.db")
        
        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
        # Brands & search terms configuration
        self.brands_search_terms: Dict[str, List[str]] = {
            "Mamaearth": [
                "Mamaearth", 
                "Mama Earth", 
                "Mamaearth products", 
                "Mamaearth shampoo", 
                "Mamaearth skincare"
            ],
            "Minimalist": [
                "Minimalist", 
                "Be Minimalist", 
                "Minimalist serum", 
                "Minimalist niacinamide", 
                "Minimalist skincare"
            ]
        }
        
        # Subreddits list for configuration-driven target searches
        self.target_subreddits: List[str] = [
            "IndianSkincareAddicts",
            "SkincareAddiction",
            "AsianBeauty",
            "Beauty",
            "IndianBeautyDeals"
        ]
        
    def validate_reddit_creds(self) -> bool:
        """
        Validates that required Reddit PRAW credentials are set.
        
        Returns:
            bool: True if valid, False otherwise.
        """
        missing = []
        if not self.reddit_client_id:
            missing.append("REDDIT_CLIENT_ID")
        if not self.reddit_client_secret:
            missing.append("REDDIT_CLIENT_SECRET")
            
        if missing:
            logger.warning(
                f"Missing Reddit API credentials: {', '.join(missing)}. "
                "PRAW collector will run in mock/offline mode unless credentials are provided."
            )
            return False
        return True

# Singleton instance of Config
config = Config()
