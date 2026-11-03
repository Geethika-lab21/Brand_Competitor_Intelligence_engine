import re
from typing import List, Union
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from src.utils.logger import logger

class TextPreprocessor:
    """
    Text preprocessing pipeline for NLP and sentiment analysis tasks.
    Performs URL removal, tokenization, stopword removal, and lemmatization.
    """

    def __init__(self) -> None:
        """
        Initializes the preprocessor and ensures NLTK dependencies are loaded.
        """
        self._ensure_nltk_resources()
        self.stop_words = set(stopwords.words("english"))
        self.lemmatizer = WordNetLemmatizer()

    def _ensure_nltk_resources(self) -> None:
        """
        Dynamically downloads NLTK resources if not already present.
        """
        resources = {
            "corpora/stopwords": "stopwords",
            "corpora/wordnet": "wordnet",
            "corpora/omw-1.4": "omw-1.4",
            "tokenizers/punkt": "punkt",
            "tokenizers/punkt_tab": "punkt_tab"
        }
        for path, name in resources.items():
            try:
                nltk.data.find(path)
            except LookupError:
                logger.info(f"Downloading required NLTK resource: '{name}'")
                nltk.download(name, quiet=True)

    def remove_urls(self, text: str) -> str:
        """
        Removes URLs starting with http/https or www.
        """
        if not isinstance(text, str):
            return ""
        # Match http://, https://, or www.
        return re.sub(r"https?://\S+|www\.\S+", "", text)

    def remove_special_characters(self, text: str) -> str:
        """
        Removes all characters except alphanumeric and whitespace.
        """
        if not isinstance(text, str):
            return ""
        # Keep letters, numbers, and spaces
        return re.sub(r"[^a-zA-Z0-9\s]", "", text)

    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """
        Filters out common English stopwords from a token list.
        """
        return [token for token in tokens if token.lower() not in self.stop_words]

    def lemmatize_text(self, tokens: List[str]) -> List[str]:
        """
        Lemmatizes each token in the token list using WordNet.
        """
        # We lemmatize assuming noun class by default
        return [self.lemmatizer.lemmatize(token) for token in tokens]

    def preprocess_text(self, text: str) -> str:
        """
        Applies the full preprocessing pipeline:
        1. Lowercasing
        2. URL removal
        3. Special character removal
        4. Tokenization
        5. Stopwords removal
        6. Lemmatization
        
        Args:
            text (str): Raw input text.
            
        Returns:
            str: Preprocessed space-separated token string.
        """
        if not text or not isinstance(text, str):
            return ""

        # 1. Lowercase
        cleaned = text.lower()
        
        # 2. URL Removal
        cleaned = self.remove_urls(cleaned)
        
        # 3. Special Character Removal
        cleaned = self.remove_special_characters(cleaned)
        
        # 4. Tokenization
        tokens = word_tokenize(cleaned)
        
        # 5. Stopwords Removal
        tokens = self.remove_stopwords(tokens)
        
        # 6. Lemmatization
        tokens = self.lemmatize_text(tokens)
        
        # Join back
        return " ".join(tokens).strip()

    def preprocess_dataframe(
        self, df: pd.DataFrame, text_columns: Union[str, List[str]], target_column: str = "clean_text"
    ) -> pd.DataFrame:
        """
        Applies text preprocessing to specified column(s) in a pandas DataFrame.
        If multiple columns are provided, they are concatenated (separated by space)
        before being cleaned.
        
        Args:
            df (pd.DataFrame): Input DataFrame.
            text_columns (Union[str, List[str]]): Column name or list of column names containing text.
            target_column (str): Name of the generated cleaned column.
            
        Returns:
            pd.DataFrame: DataFrame with the new cleaned column added.
        """
        df_copy = df.copy()
        
        if isinstance(text_columns, str):
            # Fill NaN values with empty string before cleaning
            raw_series = df_copy[text_columns].fillna("")
        else:
            # Concatenate multiple text columns
            raw_series = df_copy[text_columns].fillna("").agg(" ".join, axis=1)

        # Apply preprocessing
        df_copy[target_column] = raw_series.apply(self.preprocess_text)
        return df_copy
