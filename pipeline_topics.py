import os
import time
import pandas as pd
from src.utils.logger import logger
from src.topic_modeling.topic_extractor import TopicExtractor
from src.topic_modeling.topic_reports import generate_topic_reports
from src.topic_modeling.topic_visualizations import generate_topic_visualizations

def run_topic_modeling_pipeline() -> None:
    """
    Main orchestrator for Phase 5 VoC & Topic Modeling Engine:
    1. Loads high-confidence positive and negative sentiment records.
    2. Runs the adaptive topic modeling pipeline (BERTopic -> NMF -> Lexical).
    3. Computes topic frequencies, cross-brand gaps, and sentiment matrix.
    4. Saves reports: CSV pain/praise points, gaps, matrix, unmapped topics.
    5. Saves business markdown reports: competitor intelligence, recommendations, exec brief.
    6. Renders Plotly interactive HTML figures.
    """
    logger.info("==========================================")
    logger.info("Starting Phase 5 Voice of Customer & Topic Modeling Pipeline")
    logger.info("==========================================")

    reports_dir = "reports"
    figures_dir = os.path.join(reports_dir, "figures")
    data_dir = "data"

    pos_file = os.path.join(reports_dir, "high_confidence_positive.csv")
    neg_file = os.path.join(reports_dir, "high_confidence_negative.csv")
    results_file = os.path.join(data_dir, "sentiment_results.csv")

    # 1. Load Data
    df_pos = pd.DataFrame()
    df_neg = pd.DataFrame()

    if os.path.exists(pos_file):
        logger.info(f"Loading high confidence positive reviews from {pos_file}...")
        df_pos = pd.read_csv(pos_file)
    if os.path.exists(neg_file):
        logger.info(f"Loading high confidence negative reviews from {neg_file}...")
        df_neg = pd.read_csv(neg_file)

    # Backup Ingestion from sentiment_results.csv
    if df_pos.empty or df_neg.empty:
        if os.path.exists(results_file):
            logger.info(f"High-confidence source CSVs missing or empty. Regenerating from {results_file}...")
            results_df = pd.read_csv(results_file)
            if not results_df.empty:
                df_pos = results_df[(results_df["sentiment_label"] == "positive") & (results_df["sentiment_confidence"] >= 0.80)]
                df_neg = results_df[(results_df["sentiment_label"] == "negative") & (results_df["sentiment_confidence"] >= 0.80)]
        else:
            logger.error("No sentiment results data found. Topic modeling pipeline aborted.")
            return

    logger.info(f"Loaded {len(df_pos)} positive and {len(df_neg)} negative high confidence documents.")

    # 2. Extract Topics
    extractor = TopicExtractor()
    
    logger.info("Extracting topics for praise/positive reviews...")
    df_pos_annotated, diagnostics_pos = extractor.extract_topics(df_pos, is_positive=True)
    
    logger.info("Extracting topics for complaints/negative reviews...")
    df_neg_annotated, diagnostics_neg = extractor.extract_topics(df_neg, is_positive=False)

    # 3. Generate Reports
    # Reads results_df for general reference
    results_df = pd.read_csv(results_file) if os.path.exists(results_file) else pd.DataFrame()
    
    generate_topic_reports(
        df_pos_annotated=df_pos_annotated,
        df_neg_annotated=df_neg_annotated,
        results_df=results_df,
        diagnostics_pos=diagnostics_pos,
        diagnostics_neg=diagnostics_neg,
        reports_dir=reports_dir
    )

    # 4. Generate Visualizations
    pain_csv = os.path.join(reports_dir, "customer_pain_points.csv")
    praise_csv = os.path.join(reports_dir, "customer_praise_points.csv")
    
    pain_df = pd.read_csv(pain_csv) if os.path.exists(pain_csv) else pd.DataFrame()
    praise_df = pd.read_csv(praise_csv) if os.path.exists(praise_csv) else pd.DataFrame()

    generate_topic_visualizations(
        pain_df=pain_df,
        praise_df=praise_df,
        figures_dir=figures_dir
    )

    logger.info("==========================================")
    logger.info("Phase 5 Voice of Customer Pipeline Completed Successfully!")
    logger.info("==========================================")

if __name__ == "__main__":
    run_topic_modeling_pipeline()
