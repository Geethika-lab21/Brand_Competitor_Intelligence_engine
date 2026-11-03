from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseSource(ABC):
    """
    Abstract Base Class for Brand Intelligence Data Sources.
    Defines a unified interface to load and format customer feedback from various platforms.
    """
    
    @abstractmethod
    def fetch_data(self, brand_name: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieves data for a specified brand and formats it into the standardized schema.
        
        Args:
            brand_name (str): The brand to query (e.g., 'Mamaearth', 'Minimalist').
            
        Returns:
            List[Dict[str, Any]]: Standardized records list. Each record matches the schema:
                - source (str): Name of the data source (e.g., 'reddit', 'amazon', 'nykaa').
                - source_record_id (str): Unique identifier from the source platform.
                - brand (str): Name of the brand.
                - title (str, optional): Title of the post or review. Can be None.
                - text (str): Main review body or post content.
                - rating (float, optional): Star rating between 1.0 and 5.0. Can be None.
                - author (str, optional): Username or reviewer name. Can be None.
                - created_at (float): Epoch timestamp of the post/review creation.
                - metadata (dict): A dictionary of source-specific attributes (e.g., subreddit, score).
        """
        pass
