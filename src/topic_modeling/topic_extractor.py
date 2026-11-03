import os
import re
import time
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

# Try to import sklearn for NMF fallback
SKLEARN_AVAILABLE = False
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import NMF
    SKLEARN_AVAILABLE = True
except ImportError:
    pass

# Try to import BERTopic
BERTOPIC_AVAILABLE = False
try:
    from bertopic import BERTopic
    BERTOPIC_AVAILABLE = True
except ImportError:
    pass

from src.utils.logger import logger

# 1. Product-Domain Business Taxonomy Keywords
BUSINESS_TAXONOMY_NEG = {
    "Hair Fall": ["hairfall", "hair fall", "fall", "shampoo", "clumps", "hair", "bald", "scalp", "shedding", "thinning", "dandruff", "hair loss", "fragile", "hairfall control"],
    "Skin Irritation": ["irritation", "burning", "redness", "rash", "allergy", "irritated", "itching", "itch", "swelling", "allergic", "reaction", "skin burns", "chemicals", "chemical"],
    "Breakouts": ["breakout", "pimple", "acne", "pimples", "breakouts", "break out", "acne prone", "acne prone skin"],
    "Price Concerns": ["price", "expensive", "cost", "cheap", "waste money", "overpriced", "worthless", "pricing", "budget", "pricey", "quantity less", "less quantity", "too costly", "costly"],
    "Packaging Issues": ["packaging", "bottle", "pump", "dispenser", "leak", "cap", "cracked", "broken", "package", "spray", "dropper", "damaged", "leaking", "torn", "nozzle"],
    "White Cast": ["white cast", "whitecast", "cast", "patches", "patchy", "white patches", "chalky", "ghost"],
    "Strong Fragrance": ["strong smell", "bad smell", "fragrance", "smell", "strong fragrance", "scent", "chemical smell", "perfume", "bad odor", "heavy smell"],
    "Delivery Issues": ["delivery", "delay", "shipping", "shipped", "arrived", "late", "courier", "package", "order", "sent", "wrong product", "delivery delays"],
    "Product Ineffectiveness": ["ineffective", "useless", "worst", "bad", "worst product", "bad product", "disappointed", "no results", "waste", "not working", "useless product", "disgusting", "pathetic", "waste of money", "waste of time", "not worth", "regret", "dryness", "dry", "greasy", "sticky", "oiliness", "oily", "sweat", "sweating", "heavy", "smudge", "smudges", "smudging", "watery"]
}

BUSINESS_TAXONOMY_POS = {
    "Visible Results": ["results", "improvement", "working", "visible", "healed", "glowing", "glow", "brightening", "cleared", "clearing", "scars", "acne spots", "spots", "miracle", "works", "effective", "shiny", "shine", "softness", "silky", "bouncy", "bounce", "smoothness", "cleansing", "cleanse"],
    "Skin Hydration": ["hydrating", "moisturizer", "moisturise", "dryness", "hydration", "hydrated", "moisturised", "dry skin", "nourishing", "moisture", "serum", "creamy", "cream"],
    "Effective Ingredients": ["ingredient", "niacinamide", "salicylic", "actives", "acid", "zinc", "peeling", "ingredients", "vit c", "vitamin c", "aloe", "tea tree", "formula", "actives percentage"],
    "Good Packaging": ["packaging", "bottle", "aesthetic", "dropper", "glass", "pump", "dispenser", "pack", "package", "travel friendly"],
    "Pleasant Fragrance": ["fragrance", "smell", "scent", "odor", "aroma", "perfume", "strawberry", "mint", "delicious", "yummy", "pleasant", "nice smell", "good smell", "amazing smell"],
    "Lightweight Formula": ["lightweight", "blends", "smooth", "formula", "light", "non-sticky", "glide", "texture", "soft", "blendable", "absorption", "absorbs", "creasy", "consistency", "non greasy", "not greasy", "feather light", "non-greasy"],
    "Repurchase Intent": ["repurchase", "buy again", "recommend", "purchase again", "must buy", "worth buying", "will buy", "ordered again"],
    "Value For Money": ["value", "affordable", "worth", "money", "cheap", "pricing", "budget", "deal", "worth buying", "worth every penny", "price is good", "discount"],
    "Product Quality": ["good", "amazing", "great", "love", "nice", "best", "perfect", "quality", "satisfied", "excellent", "awesome", "good product", "great product", "shade", "pigmentation", "pigmented", "glitter", "shimmer", "coverage", "look", "finish", "matte"]
}



class TopicExtractor:
    """
    Extracts customer reviews topics using an adaptive model hierarchy:
    1. BERTopic (Preferred for large corpora)
    2. NMF Fallback (If BERTopic is missing and document count is sufficient)
    3. Lexical Fallback (If corpus is too small or libraries are missing)
    """

    def __init__(self, force_fallback: Optional[str] = "lexical") -> None:
        """
        Initializes the Topic Extractor.
        
        Args:
            force_fallback (Optional[str]): Force a specific fallback ('lexical' or 'nmf') for testing. Defaults to 'lexical'.
        """
        self.force_fallback = force_fallback
        self.model_used = "Lexical Category Fallback"
        self.topics_count = 0

    def extract_topics(
        self, df: pd.DataFrame, is_positive: bool = True, min_docs_for_modeling: int = 15
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Runs the extraction pipeline, annotating the input DataFrame with 'raw_topic' and 'mapped_topic'.
        
        Args:
            df (pd.DataFrame): Input dataframe containing 'text' and 'title'.
            is_positive (bool): True for positive praise analysis, False for complaints.
            min_docs_for_modeling (int): Minimum document threshold to allow NMF/BERTopic.
            
        Returns:
            Tuple[pd.DataFrame, Dict[str, Any]]: 
                - Annotated DataFrame with columns: raw_topic, mapped_topic.
                - Diagnostics dictionary.
        """
        start_time = time.time()
        
        if df.empty:
            return df.copy(), {
                "model_used": "None",
                "topics_discovered": 0,
                "records_analyzed": 0,
                "processing_time_sec": round(time.time() - start_time, 4)
            }

        # Combine title and text to get rich context
        texts = []
        for _, row in df.iterrows():
            title = str(row["title"]) + " " if pd.notnull(row.get("title")) else ""
            body = str(row["text"]) if pd.notnull(row.get("text")) else ""
            texts.append((title + body).strip())

        df_out = df.copy()
        taxonomy = BUSINESS_TAXONOMY_POS if is_positive else BUSINESS_TAXONOMY_NEG

        # Determine strategy
        num_docs = len(df)
        use_lexical = (
            self.force_fallback == "lexical"
            or num_docs < min_docs_for_modeling
            or not SKLEARN_AVAILABLE
        )
        use_nmf = (
            not use_lexical 
            and (self.force_fallback == "nmf" or not BERTOPIC_AVAILABLE)
        )
        use_bertopic = not use_lexical and not use_nmf and BERTOPIC_AVAILABLE

        if use_bertopic:
            try:
                self.model_used = "BERTopic"
                df_out = self._run_bertopic(df_out, texts, taxonomy)
            except Exception as e:
                logger.warning(f"BERTopic execution failed: {e}. Falling back to NMF.")
                use_nmf = True

        if use_nmf:
            try:
                self.model_used = "NMF Fallback"
                df_out = self._run_nmf(df_out, texts, taxonomy)
            except Exception as e:
                logger.warning(f"NMF execution failed: {e}. Falling back to Lexical analysis.")
                use_lexical = True

        if use_lexical:
            self.model_used = "Lexical Category Fallback"
            df_out = self._run_lexical(df_out, texts, taxonomy)

        elapsed = time.time() - start_time
        
        # Calculate distinct non-unmapped topics
        unique_topics = set(df_out["mapped_topic"].unique())
        unique_topics.discard("Unmapped")
        self.topics_count = len(unique_topics)

        diagnostics = {
            "model_used": self.model_used,
            "topics_discovered": self.topics_count,
            "records_analyzed": len(df_out),
            "processing_time_sec": round(elapsed, 4)
        }

        return df_out, diagnostics

    def _map_keywords_to_taxonomy(
        self, keywords: List[str], taxonomy: Dict[str, List[str]]
    ) -> str:
        """
        Compares list of keywords (e.g. from NMF topic words) with the taxonomy keyword lists,
        returning the matching business category. If no matches, returns 'Unmapped'.
        """
        best_category = "Unmapped"
        max_matches = 0

        for category, tax_words in taxonomy.items():
            matches = sum(1 for w in keywords if w.lower() in tax_words)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        return best_category

    def _run_lexical(
        self, df: pd.DataFrame, texts: List[str], taxonomy: Dict[str, List[str]]
    ) -> pd.DataFrame:
        """
        Categorizes documents based on keyword/phrase occurrences with word boundaries (optimized).
        """
        # Pre-compile patterns for each category
        compiled_patterns = {}
        for category, keywords in taxonomy.items():
            sorted_keywords = sorted(keywords, key=len, reverse=True)
            pattern_str = r"\b(" + "|".join(re.escape(w) for w in sorted_keywords) + r")\b"
            compiled_patterns[category] = re.compile(pattern_str)

        raw_topics = []
        mapped_topics = []

        for text in texts:
            text_lower = text.lower()
            best_cat = "Unmapped"
            max_matches = 0
            matching_keywords = []

            for category, pattern in compiled_patterns.items():
                matches = pattern.findall(text_lower)
                unique_matches = list(set(matches))
                num_matches = len(unique_matches)
                
                if num_matches > max_matches:
                    max_matches = num_matches
                    best_cat = category
                    matching_keywords = unique_matches

            mapped_topics.append(best_cat)
            
            # Formulate a raw topic representation from matched keywords or text snippet
            if best_cat != "Unmapped":
                raw_topics.append(", ".join(matching_keywords[:3]))
            else:
                # For unmapped texts, find top 2 words in text that are nouns/adjectives
                # Exclude basic skincare stopwords
                stopwords = {"the", "and", "this", "for", "with", "that", "butt", "oil", "face", "wash", "product", "using", "skin", "my", "was", "but", "not"}
                clean_words = [w for w in re.findall(r"\b\w{3,}\b", text_lower) if w not in stopwords]
                raw_repr = ", ".join(clean_words[:3]) if clean_words else "general feedback"
                raw_topics.append(raw_repr)

        df["raw_topic"] = raw_topics
        df["mapped_topic"] = mapped_topics
        return df


    def _run_nmf(
        self, df: pd.DataFrame, texts: List[str], taxonomy: Dict[str, List[str]]
    ) -> pd.DataFrame:
        """
        Applies TF-IDF + Non-Negative Matrix Factorization (NMF) to cluster reviews.
        """
        # Determine number of topics dynamically to prevent errors
        n_topics = min(5, max(2, len(texts) // 3))
        
        # 1. Compute TF-IDF
        vectorizer = TfidfVectorizer(stop_words="english", max_features=500, ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        # 2. Fit NMF Model
        nmf_model = NMF(n_components=n_topics, random_state=42, max_iter=400)
        nmf_model.fit(tfidf_matrix)
        
        # Extract top keywords per topic
        feature_names = vectorizer.get_feature_names_out()
        topic_raw_terms = []
        topic_mappings = {}

        for topic_idx, topic in enumerate(nmf_model.components_):
            top_indices = topic.argsort()[::-1][:5]
            top_words = [feature_names[i] for i in top_indices]
            raw_repr = ", ".join(top_words[:3])
            topic_raw_terms.append(raw_repr)
            
            # Map top words to taxonomy category
            mapped_cat = self._map_keywords_to_taxonomy(top_words, taxonomy)
            topic_mappings[topic_idx] = (raw_repr, mapped_cat)

        # 3. Assign documents to highest-score topic
        doc_topic_matrix = nmf_model.transform(tfidf_matrix)
        doc_topics = doc_topic_matrix.argmax(axis=1)

        raw_topics = []
        mapped_topics = []

        for idx, topic_idx in enumerate(doc_topics):
            # If the max score is extremely low, label as unmapped
            if doc_topic_matrix[idx, topic_idx] < 1e-4:
                raw_topics.append("general feedback")
                mapped_topics.append("Unmapped")
            else:
                raw_repr, mapped_cat = topic_mappings[topic_idx]
                raw_topics.append(raw_repr)
                mapped_topics.append(mapped_cat)

        df["raw_topic"] = raw_topics
        df["mapped_topic"] = mapped_topics
        return df

    def _run_bertopic(
        self, df: pd.DataFrame, texts: List[str], taxonomy: Dict[str, List[str]]
    ) -> pd.DataFrame:
        """
        Applies BERTopic modeling to cluster reviews and extracts themes.
        """
        # Initialize BERTopic model
        # Using a small embedding model or default sentence-transformers
        topic_model = BERTopic(calculate_probabilities=True, verbose=False)
        topics, probs = topic_model.fit_transform(texts)

        # Get representative words for each cluster
        topic_info = topic_model.get_topic_info()
        topic_mappings = {}

        # Loop through discovered topics (excluding outlier cluster -1)
        for _, row in topic_info.iterrows():
            topic_idx = int(row["Topic"])
            if topic_idx == -1:
                topic_mappings[topic_idx] = ("general feedback", "Unmapped")
                continue

            words_info = topic_model.get_topic(topic_idx)
            top_words = [w[0] for w in words_info[:5]] if words_info else []
            raw_repr = ", ".join(top_words[:3]) if top_words else f"Topic {topic_idx}"
            
            mapped_cat = self._map_keywords_to_taxonomy(top_words, taxonomy)
            topic_mappings[topic_idx] = (raw_repr, mapped_cat)

        raw_topics = []
        mapped_topics = []

        for t in topics:
            raw_repr, mapped_cat = topic_mappings.get(t, ("general feedback", "Unmapped"))
            raw_topics.append(raw_repr)
            mapped_topics.append(mapped_cat)

        df["raw_topic"] = raw_topics
        df["mapped_topic"] = mapped_topics
        return df
