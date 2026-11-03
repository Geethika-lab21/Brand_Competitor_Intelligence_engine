import os
import re
from typing import List, Dict, Any, Tuple
from collections import Counter
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio
from sklearn.feature_extraction.text import TfidfVectorizer
from src.utils.logger import logger
from src.utils.database_helper import DatabaseHelper

# Set default Plotly template to a clean, modern style
pio.templates.default = "plotly_white"

class ExploratoryAnalyzer:
    """
    Orchestrates Exploratory Data Analysis (EDA) on collected brand datasets.
    Extracts brand metrics, subreddit coverage, word frequencies, N-grams,
    TF-IDF vectors, time-series growth, and generates Plotly interactive visualizations.
    """

    def __init__(self, db_helper: DatabaseHelper, preprocessed_posts_path: str, preprocessed_comments_path: str) -> None:
        """
        Initializes the Exploratory Analyzer.
        
        Args:
            db_helper (DatabaseHelper): Database helper for relational database queries.
            preprocessed_posts_path (str): File path to the preprocessed posts CSV.
            preprocessed_comments_path (str): File path to the preprocessed comments CSV.
        """
        self.db_helper = db_helper
        self.preprocessed_posts_path = preprocessed_posts_path
        self.preprocessed_comments_path = preprocessed_comments_path
        
        # Load raw data from database
        self.raw_posts_df, self.raw_comments_df = self._load_raw_database_data()
        # Load preprocessed text from CSVs
        self.prep_posts_df, self.prep_comments_df = self._load_preprocessed_csv_data()

    def _load_raw_database_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Queries SQLite to retrieve raw posts and comments with joined brand names.
        """
        try:
            with self.db_helper.get_connection() as conn:
                posts_query = """
                SELECT p.*, b.name AS brand_name 
                FROM posts p
                JOIN brands b ON p.brand_id = b.id;
                """
                comments_query = """
                SELECT c.*, b.name AS brand_name 
                FROM comments c
                JOIN brands b ON c.brand_id = b.id;
                """
                posts = pd.read_sql_query(posts_query, conn)
                comments = pd.read_sql_query(comments_query, conn)
            return posts, comments
        except Exception as e:
            logger.error(f"Error querying raw tables from SQLite: {e}", exc_info=True)
            return pd.DataFrame(), pd.DataFrame()

    def _load_preprocessed_csv_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads Phase 1 preprocessed CSV files.
        """
        try:
            posts = pd.read_csv(self.preprocessed_posts_path) if os.path.exists(self.preprocessed_posts_path) else pd.DataFrame()
            comments = pd.read_csv(self.preprocessed_comments_path) if os.path.exists(self.preprocessed_comments_path) else pd.DataFrame()
            logger.info("Loaded preprocessed text CSVs for text analytics.")
            return posts, comments
        except Exception as e:
            logger.error(f"Error loading preprocessed CSVs: {e}", exc_info=True)
            return pd.DataFrame(), pd.DataFrame()

    # --- 1. Brand Analytics ---
    
    def generate_brand_analytics(self, reports_dir: str) -> pd.DataFrame:
        """
        Analyzes posts, comments, unique authors, and co-mentions per brand.
        Saves summaries to reports/brand_summary.csv and reports/brand_comentions.csv.
        
        Returns:
            pd.DataFrame: Brand summary stats.
        """
        logger.info("Executing Brand Analytics...")
        os.makedirs(reports_dir, exist_ok=True)
        
        if self.raw_posts_df.empty:
            logger.warning("No posts available for brand analysis.")
            return pd.DataFrame()

        # Posts per brand
        post_counts = self.raw_posts_df["brand_name"].value_counts().to_dict()
        # Comments per brand
        comment_counts = self.raw_comments_df["brand_name"].value_counts().to_dict() if not self.raw_comments_df.empty else {}
        
        # Unique authors per brand (posts + comments)
        brand_authors = {}
        for brand in post_counts.keys():
            p_auths = set(self.raw_posts_df[self.raw_posts_df["brand_name"] == brand]["author"].dropna().unique())
            c_auths = set()
            if not self.raw_comments_df.empty:
                c_auths = set(self.raw_comments_df[self.raw_comments_df["brand_name"] == brand]["author"].dropna().unique())
            brand_authors[brand] = len(p_auths.union(c_auths))

        # Build brand summary dataframe
        brands = list(post_counts.keys())
        summary_data = []
        for b in brands:
            summary_data.append({
                "brand": b,
                "posts_count": post_counts.get(b, 0),
                "comments_count": comment_counts.get(b, 0),
                "unique_authors": brand_authors.get(b, 0)
            })
        brand_summary_df = pd.DataFrame(summary_data)
        brand_summary_df.to_csv(os.path.join(reports_dir, "brand_summary.csv"), index=False)
        
        # Brand Co-mention Analysis
        # Co-mention occurs when both brands are mentioned. 
        # In our database, a post can co-mention both brands, and we count instances in selftext/title.
        co_mentions_list = []
        for idx, row in self.raw_posts_df.iterrows():
            text = f"{row['title']} {row['body']}".lower()
            mentions_mama = "mamaearth" in text or "mama earth" in text
            mentions_mini = "minimalist" in text or "be minimalist" in text or "beminimalist" in text
            
            if mentions_mama and mentions_mini:
                co_mentions_list.append({
                    "id": row["id"],
                    "title": row["title"],
                    "subreddit": row["subreddit"],
                    "author": row["author"],
                    "score": row["score"],
                    "created_utc": row["created_utc"],
                    "source": row["source"]
                })
        
        comentions_df = pd.DataFrame(co_mentions_list)
        comentions_df.to_csv(os.path.join(reports_dir, "brand_comentions.csv"), index=False)
        logger.info(f"Brand Analytics complete. Co-mentions count: {len(comentions_df)}")
        return brand_summary_df

    # --- 2. Subreddit Analytics ---
    
    def generate_subreddit_analytics(self, reports_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Analyzes the distribution of posts and comments across subreddits.
        Saves subreddit_summary.csv.
        
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: Subreddit post and comment summaries.
        """
        logger.info("Executing Subreddit Analytics...")
        os.makedirs(reports_dir, exist_ok=True)
        
        if self.raw_posts_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # Posts per subreddit
        sub_posts = self.raw_posts_df.groupby(["subreddit", "brand_name"]).size().reset_index(name="posts_count")
        sub_posts_pivot = sub_posts.pivot(index="subreddit", columns="brand_name", values="posts_count").fillna(0).astype(int)
        sub_posts_pivot["total_posts"] = sub_posts_pivot.sum(axis=1)
        sub_posts_pivot = sub_posts_pivot.sort_values(by="total_posts", ascending=False).reset_index()

        # Comments per subreddit
        sub_comments_pivot = pd.DataFrame(columns=["subreddit", "total_comments"])
        if not self.raw_comments_df.empty:
            sub_coms = self.raw_comments_df.groupby(["subreddit", "brand_name"]).size().reset_index(name="comments_count")
            sub_comments_pivot = sub_coms.pivot(index="subreddit", columns="brand_name", values="comments_count").fillna(0).astype(int)
            sub_comments_pivot["total_comments"] = sub_comments_pivot.sum(axis=1)
            sub_comments_pivot = sub_comments_pivot.sort_values(by="total_comments", ascending=False).reset_index()

        # Merge summary
        summary_df = pd.merge(
            sub_posts_pivot[["subreddit", "total_posts"]],
            sub_comments_pivot[["subreddit", "total_comments"]] if "subreddit" in sub_comments_pivot.columns else pd.DataFrame(columns=["subreddit", "total_comments"]),
            on="subreddit",
            how="outer"
        ).fillna(0)
        summary_df["total_posts"] = summary_df["total_posts"].astype(int)
        summary_df["total_comments"] = summary_df["total_comments"].astype(int)
        summary_df["engagement_score"] = summary_df["total_posts"] + summary_df["total_comments"]
        summary_df = summary_df.sort_values(by="engagement_score", ascending=False)
        
        summary_df.to_csv(os.path.join(reports_dir, "subreddit_summary.csv"), index=False)
        logger.info("Subreddit Analytics complete.")
        return sub_posts_pivot, summary_df

    # --- 3. Text Analytics (N-grams & Distributions) ---
    
    def extract_ngrams(self, texts: List[str], n: int = 1) -> List[Tuple[str, int]]:
        """
        Helper function to extract word N-grams from a list of clean text strings.
        """
        ngrams_list = []
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                continue
            words = text.split()
            if len(words) < n:
                continue
            
            # Generate word level tuples
            if n == 1:
                ngrams_list.extend(words)
            else:
                ngram_tuples = [tuple(words[i:i+n]) for i in range(len(words)-n+1)]
                ngrams_list.extend([" ".join(t) for t in ngram_tuples])
                
        return Counter(ngrams_list).most_common(50)

    def generate_text_analytics(self, reports_dir: str) -> Dict[str, pd.DataFrame]:
        """
        Generates N-grams frequency lists, text lengths, and word count statistics.
        Exports word_frequency.csv, bigram_frequency.csv, and trigram_frequency.csv.
        """
        logger.info("Executing Text Analytics...")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Merge cleaned posts and comments text columns
        p_texts = self.prep_posts_df["clean_text"].dropna().tolist() if not self.prep_posts_df.empty else []
        c_texts = self.prep_comments_df["clean_text"].dropna().tolist() if not self.prep_comments_df.empty else []
        all_texts = p_texts + c_texts

        if not all_texts:
            logger.warning("No preprocessed texts available for text analytics.")
            return {}

        # Unigrams (1-grams)
        unigrams = self.extract_ngrams(all_texts, n=1)
        unigrams_df = pd.DataFrame(unigrams, columns=["ngram", "frequency"])
        unigrams_df.to_csv(os.path.join(reports_dir, "word_frequency.csv"), index=False)

        # Bigrams (2-grams)
        bigrams = self.extract_ngrams(all_texts, n=2)
        bigrams_df = pd.DataFrame(bigrams, columns=["ngram", "frequency"])
        bigrams_df.to_csv(os.path.join(reports_dir, "bigram_frequency.csv"), index=False)

        # Trigrams (3-grams)
        trigrams = self.extract_ngrams(all_texts, n=3)
        trigrams_df = pd.DataFrame(trigrams, columns=["ngram", "frequency"])
        trigrams_df.to_csv(os.path.join(reports_dir, "trigram_frequency.csv"), index=False)

        # Statistics computation
        # Compute lengths and word counts
        lengths = []
        word_counts = []
        for text in all_texts:
            if isinstance(text, str):
                lengths.append(len(text))
                word_counts.append(len(text.split()))

        stats_df = pd.DataFrame({
            "character_length": lengths,
            "word_count": word_counts
        })
        
        logger.info("Text Analytics complete.")
        return {
            "unigrams": unigrams_df,
            "bigrams": bigrams_df,
            "trigrams": trigrams_df,
            "stats": stats_df
        }

    # --- 4. Brand TF-IDF Analysis ---
    
    def generate_tfidf_analytics(self, reports_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Computes TF-IDF metrics for Mamaearth and Minimalist separately.
        Exports tfidf_mamaearth.csv and tfidf_minimalist.csv.
        """
        logger.info("Executing TF-IDF Analysis per brand...")
        os.makedirs(reports_dir, exist_ok=True)
        
        if self.prep_posts_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        def run_tfidf(df: pd.DataFrame, brand: str) -> pd.DataFrame:
            # Filter rows by brand
            brand_df = df[df["brand_name"] == brand]
            
            # Combine title + body cleaned texts (or just use preprocessed text)
            # If prep csv has clean_text, we use it. If not, fallback.
            texts = brand_df["clean_text"].dropna().tolist()
            
            if not texts or len(texts) == 0:
                logger.warning(f"No text data found for TF-IDF brand: {brand}")
                return pd.DataFrame(columns=["word", "tfidf_score"])
            
            try:
                # Initialize scikit-learn TF-IDF vectorizer
                vectorizer = TfidfVectorizer(max_df=0.9, min_df=1, stop_words="english")
                tfidf_matrix = vectorizer.fit_transform(texts)
                feature_names = vectorizer.get_feature_names_out()
                mean_scores = tfidf_matrix.mean(axis=0).A1
                
                tfidf_df = pd.DataFrame({"word": feature_names, "tfidf_score": mean_scores})
                tfidf_df = tfidf_df.sort_values(by="tfidf_score", ascending=False).reset_index(drop=True)
                return tfidf_df.head(50)
            except Exception as e:
                logger.error(f"Error computing TF-IDF for brand '{brand}': {e}")
                return pd.DataFrame(columns=["word", "tfidf_score"])

        # Compute TF-IDF for Mamaearth and Minimalist
        # We concatenate posts and comments for the brand
        full_posts_coms = pd.concat([self.prep_posts_df, self.prep_comments_df], ignore_index=True)
        
        tfidf_mamaearth = run_tfidf(full_posts_coms, "Mamaearth")
        tfidf_minimalist = run_tfidf(full_posts_coms, "Minimalist")

        tfidf_mamaearth.to_csv(os.path.join(reports_dir, "tfidf_mamaearth.csv"), index=False)
        tfidf_minimalist.to_csv(os.path.join(reports_dir, "tfidf_minimalist.csv"), index=False)
        logger.info("TF-IDF Analysis complete.")
        return tfidf_mamaearth, tfidf_minimalist

    # --- 5. Time-Series Analysis ---
    
    def generate_time_series_analytics(self, reports_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Aggregates posts and comments volumes grouped by year-month.
        Exports posts_per_month.csv and comments_per_month.csv.
        """
        logger.info("Executing Time-Series Analytics...")
        os.makedirs(reports_dir, exist_ok=True)
        
        def group_by_month(df: pd.DataFrame) -> pd.DataFrame:
            if df.empty or "created_utc" not in df.columns:
                return pd.DataFrame(columns=["year_month", "count"])
            
            # Convert utc to datetime
            df_copy = df.copy()
            df_copy["datetime"] = pd.to_datetime(df_copy["created_utc"], unit="s")
            df_copy["year_month"] = df_copy["datetime"].dt.to_period("M").astype(str)
            
            grouped = df_copy.groupby(["year_month", "brand_name"]).size().reset_index(name="count")
            # Pivot to have brand columns
            pivoted = grouped.pivot(index="year_month", columns="brand_name", values="count").fillna(0).astype(int)
            pivoted["total"] = pivoted.sum(axis=1)
            return pivoted.reset_index()

        posts_per_month = group_by_month(self.raw_posts_df)
        comments_per_month = group_by_month(self.raw_comments_df)

        posts_per_month.to_csv(os.path.join(reports_dir, "posts_per_month.csv"), index=False)
        comments_per_month.to_csv(os.path.join(reports_dir, "comments_per_month.csv"), index=False)
        logger.info("Time-Series Analytics complete.")
        return posts_per_month, comments_per_month

    # --- 6. Plotly Figure Visualizations ---
    
    def generate_visualizations(self, figures_dir: str, text_analytics: Dict[str, pd.DataFrame], 
                                 posts_time: pd.DataFrame, comments_time: pd.DataFrame) -> None:
        """
        Creates interactive Plotly charts and writes them as standalone HTML files.
        """
        logger.info("Generating Plotly Visualizations...")
        os.makedirs(figures_dir, exist_ok=True)
        
        # Color palette definition
        brand_colors = {"Mamaearth": "#99cc33", "Minimalist": "#222222"} # Green and Matte Black/Grey
        
        # 1. Posts & Comments by Brand (Bar Chart)
        if not self.raw_posts_df.empty:
            fig_posts = px.bar(
                self.raw_posts_df["brand_name"].value_counts().reset_index(),
                x="brand_name",
                y="count",
                title="Total Reddit Posts by Brand",
                labels={"brand_name": "Brand", "count": "Posts Count"},
                color="brand_name",
                color_discrete_map=brand_colors
            )
            fig_posts.update_layout(showlegend=False)
            pio.write_html(fig_posts, os.path.join(figures_dir, "posts_by_brand.html"))

        if not self.raw_comments_df.empty:
            fig_comments = px.bar(
                self.raw_comments_df["brand_name"].value_counts().reset_index(),
                x="brand_name",
                y="count",
                title="Total Reddit Comments by Brand",
                labels={"brand_name": "Brand", "count": "Comments Count"},
                color="brand_name",
                color_discrete_map=brand_colors
            )
            fig_comments.update_layout(showlegend=False)
            pio.write_html(fig_comments, os.path.join(figures_dir, "comments_by_brand.html"))

        # 2. Top Subreddits (Horizontal Bar Chart)
        if not self.raw_posts_df.empty:
            top_subs = self.raw_posts_df["subreddit"].value_counts().head(10).reset_index()
            fig_subs = px.bar(
                top_subs,
                y="subreddit",
                x="count",
                orientation="h",
                title="Top 10 Most Active Subreddits",
                labels={"subreddit": "Subreddit", "count": "Post Count"},
                color="subreddit",
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_subs.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            pio.write_html(fig_subs, os.path.join(figures_dir, "top_subreddits.html"))

        # 3. Word & N-gram Frequencies (Bar Charts)
        if "unigrams" in text_analytics and not text_analytics["unigrams"].empty:
            fig_uni = px.bar(
                text_analytics["unigrams"].head(20),
                x="ngram",
                y="frequency",
                title="Top 20 Most Frequent Unigrams",
                labels={"ngram": "Word", "frequency": "Frequency"},
                color="frequency",
                color_continuous_scale="Viridis"
            )
            fig_uni.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False)
            pio.write_html(fig_uni, os.path.join(figures_dir, "word_frequency.html"))

        if "bigrams" in text_analytics and not text_analytics["bigrams"].empty:
            fig_bi = px.bar(
                text_analytics["bigrams"].head(20),
                x="ngram",
                y="frequency",
                title="Top 20 Most Frequent Bigrams",
                labels={"ngram": "Bigram", "frequency": "Frequency"},
                color="frequency",
                color_continuous_scale="Plasma"
            )
            fig_bi.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False)
            pio.write_html(fig_bi, os.path.join(figures_dir, "bigram_frequency.html"))

        # 4. Text length distributions (Histogram)
        if "stats" in text_analytics and not text_analytics["stats"].empty:
            fig_dist = px.histogram(
                text_analytics["stats"],
                x="word_count",
                nbins=30,
                title="Distribution of Word Counts across Posts & Comments",
                labels={"word_count": "Word Count", "count": "Record Count"},
                color_discrete_sequence=["#5A6B83"]
            )
            pio.write_html(fig_dist, os.path.join(figures_dir, "text_length_distribution.html"))

        # 5. Time Series plots (Line Charts)
        if not posts_time.empty and "year_month" in posts_time.columns:
            # Melt dataframe to long format for Plotly Express
            melted_posts = posts_time.melt(id_vars="year_month", value_vars=[c for c in posts_time.columns if c not in ["year_month", "total"]], var_name="brand", value_name="count")
            fig_time_posts = px.line(
                melted_posts,
                x="year_month",
                y="count",
                color="brand",
                title="Reddit Post Trends Over Time (Monthly)",
                labels={"year_month": "Month", "count": "Posts Count", "brand": "Brand"},
                color_discrete_map=brand_colors,
                markers=True
            )
            pio.write_html(fig_time_posts, os.path.join(figures_dir, "posts_over_time.html"))

        if not comments_time.empty and "year_month" in comments_time.columns:
            melted_coms = comments_time.melt(id_vars="year_month", value_vars=[c for c in comments_time.columns if c not in ["year_month", "total"]], var_name="brand", value_name="count")
            fig_time_coms = px.line(
                melted_coms,
                x="year_month",
                y="count",
                color="brand",
                title="Reddit Comment Trends Over Time (Monthly)",
                labels={"year_month": "Month", "count": "Comments Count", "brand": "Brand"},
                color_discrete_map=brand_colors,
                markers=True
            )
            pio.write_html(fig_time_coms, os.path.join(figures_dir, "comments_over_time.html"))
            
        logger.info("Plotly Visualizations saved successfully in figures/ directory.")
