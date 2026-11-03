import os
import datetime
import pandas as pd
from src.utils.logger import logger
from src.utils.config import config
from src.topic_modeling.topic_extractor import TopicExtractor
from src.metrics.kpi_definitions import (
    NET_SENTIMENT_TARGET,
    DATA_COMPLETENESS_TARGET,
    PIPELINE_HEALTH_TARGET,
    CSAT_TARGET,
    BRAND_HEALTH_TARGET,
    COMPETITIVE_POSITION_TARGET,
    get_kpi_status,
    get_brand_health_status,
    get_data_quality_status,
    get_pipeline_health_status
)
from src.metrics.brand_metrics import calculate_brand_metrics
from src.metrics.competitor_metrics import calculate_competitor_metrics, calculate_topic_ownership
from src.metrics.customer_metrics import calculate_customer_experience_metrics, generate_risk_opportunity_scorecard
from src.metrics.operational_metrics import calculate_operational_metrics
from src.metrics.star_schema import generate_star_schema

def run_bi_pipeline() -> None:
    """
    Main orchestrator for Phase 6 BI Metrics & Semantic Layer:
    1. Ingests sentiment results and annotates them with mapped topics.
    2. Computes KPIs for Brand, Competitor, Customer Experience, and Operations.
    3. Exposes centralized scorecards and Key-Value metrics summaries.
    4. Evaluates Risks and Opportunities.
    5. Exports dimensional star schema under exports/ for Power BI import.
    """
    logger.info("==========================================")
    logger.info("Starting Phase 6 BI Metrics & Semantic Layer Pipeline")
    logger.info("==========================================")

    reports_dir = "reports"
    exports_dir = "exports"
    data_dir = "data"
    db_path = config.database_path

    results_file = os.path.join(data_dir, "sentiment_results.csv")
    if not os.path.exists(results_file):
        logger.error(f"Sentiment results not found at {results_file}. Aborting BI pipeline.")
        return

    # 1. Ingest Data
    results_df = pd.read_csv(results_file)
    logger.info(f"Ingested {len(results_df)} reviews from sentiment predictions.")

    # 2. Annotate topics to enable Shannon diversity and star schema relations
    df_pos = results_df[(results_df["sentiment_label"] == "positive") & (results_df["sentiment_confidence"] >= 0.80)].copy()
    df_neg = results_df[(results_df["sentiment_label"] == "negative") & (results_df["sentiment_confidence"] >= 0.80)].copy()

    extractor = TopicExtractor()
    logger.info("Running topic categorization for positive records...")
    df_pos_annotated, _ = extractor.extract_topics(df_pos, is_positive=True)
    logger.info("Running topic categorization for negative records...")
    df_neg_annotated, _ = extractor.extract_topics(df_neg, is_positive=False)

    df_topics_combined = pd.concat([df_pos_annotated, df_neg_annotated], ignore_index=True)

    # 3. Calculate Brand Scorecards
    brands = results_df["brand"].dropna().unique().tolist()
    brand_metrics_list = []
    for b in brands:
        metrics = calculate_brand_metrics(results_df, df_topics_combined, b)
        brand_metrics_list.append(metrics)
        
    brand_scorecard = pd.DataFrame(brand_metrics_list)
    brand_scorecard_file = os.path.join(reports_dir, "brand_scorecard.csv")
    brand_scorecard.to_csv(brand_scorecard_file, index=False, encoding="utf-8")
    logger.info(f"Saved Brand Scorecard to {brand_scorecard_file}")

    # 4. Calculate Competitor Scorecard
    comp_benchmarks = calculate_competitor_metrics(results_df, df_topics_combined)
    brand_a = comp_benchmarks["brand_a"]
    brand_b = comp_benchmarks["brand_b"]
    topic_owner_df = calculate_topic_ownership(df_topics_combined, brand_a, brand_b)
    
    # Extract brand metrics for brand_a and brand_b
    brand_a_metrics = next((m for m in brand_metrics_list if m["brand_name"] == brand_a), {"net_sentiment": 0.0})
    brand_b_metrics = next((m for m in brand_metrics_list if m["brand_name"] == brand_b), {"net_sentiment": 0.0})

    # Structural scorecard for competitor comparisons
    comp_rows = [
        {"Metric": "Share of Voice (SOV) %", brand_a: comp_benchmarks["brand_a_sov"], brand_b: comp_benchmarks["brand_b_sov"], "Gap": round(comp_benchmarks["brand_b_sov"] - comp_benchmarks["brand_a_sov"], 2)},
        {"Metric": "Net Sentiment Score", brand_a: brand_a_metrics["net_sentiment"], brand_b: brand_b_metrics["net_sentiment"], "Gap": comp_benchmarks["sentiment_gap"]},
        {"Metric": "Praise Count Gap", brand_a: sum(results_df[results_df["brand"] == brand_a]["sentiment_label"] == "positive"), brand_b: sum(results_df[results_df["brand"] == brand_b]["sentiment_label"] == "positive"), "Gap": comp_benchmarks["praise_gap"]},
        {"Metric": "Complaint Count Gap", brand_a: sum(results_df[results_df["brand"] == brand_a]["sentiment_label"] == "negative"), brand_b: sum(results_df[results_df["brand"] == brand_b]["sentiment_label"] == "negative"), "Gap": comp_benchmarks["complaint_gap"]}
    ]
    comp_scorecard = pd.DataFrame(comp_rows)
    comp_scorecard_file = os.path.join(reports_dir, "competitor_scorecard.csv")
    comp_scorecard.to_csv(comp_scorecard_file, index=False, encoding="utf-8")
    logger.info(f"Saved Competitor Scorecard to {comp_scorecard_file}")

    # 5. Calculate Customer Experience Scorecard
    cx_benchmarks = calculate_customer_experience_metrics(df_pos_annotated, df_neg_annotated)
    
    # Format a row for each brand
    cx_rows = []
    for idx, b in enumerate(brands):
        brand_pos = df_pos_annotated[df_pos_annotated["brand"].str.lower() == b.lower()]
        brand_neg = df_neg_annotated[df_neg_annotated["brand"].str.lower() == b.lower()]
        cx_brand = calculate_customer_experience_metrics(brand_pos, brand_neg)
        cx_rows.append({
            "Brand": b,
            "Top Complaint Category": cx_brand["top_complaint_category"],
            "Top Praise Category": cx_brand["top_praise_category"],
            "Complaint Concentration %": cx_brand["complaint_concentration"],
            "Praise Concentration %": cx_brand["praise_concentration"]
        })
    cx_scorecard = pd.DataFrame(cx_rows)
    cx_scorecard_file = os.path.join(reports_dir, "customer_experience_scorecard.csv")
    cx_scorecard.to_csv(cx_scorecard_file, index=False, encoding="utf-8")
    logger.info(f"Saved Customer Experience Scorecard to {cx_scorecard_file}")

    # 6. Calculate Operational Scorecard
    op_metrics = calculate_operational_metrics(db_path, results_df)
    op_scorecard = pd.DataFrame([op_metrics])
    op_scorecard_file = os.path.join(reports_dir, "operational_scorecard.csv")
    op_scorecard.to_csv(op_scorecard_file, index=False, encoding="utf-8")
    logger.info(f"Saved Operational Scorecard to {op_scorecard_file}")

    # 7. Generate Risk & Opportunity Scorecard
    ro_scorecard = generate_risk_opportunity_scorecard(df_pos_annotated, df_neg_annotated)
    ro_scorecard_file = os.path.join(reports_dir, "risk_opportunity_scorecard.csv")
    ro_scorecard.to_csv(ro_scorecard_file, index=False, encoding="utf-8")
    logger.info(f"Saved Risk & Opportunity Scorecard to {ro_scorecard_file}")

    # 8. Generate Executive KPIs (Power BI Cards ready)
    # Brand Health Score = average of positive review rate and net sentiment (mapped 0-100)
    # CSAT = positive review rate
    # Competitive Position = based on SOV and Sentiment Score
    exec_kpi_rows = []
    for idx, b_metrics in enumerate(brand_metrics_list):
        b = b_metrics["brand_name"]
        
        # Calculations
        brand_health = round((b_metrics["positive_rate"] + (b_metrics["net_sentiment"] + 100) / 2) / 2, 2)
        csat = b_metrics["positive_rate"]
        
        # Competitive position score combines share of voice and net sentiment ranking
        sov = round((b_metrics["visibility"] / len(results_df) * 100), 2) if len(results_df) > 0 else 0.0
        net = b_metrics["net_sentiment"]
        comp_score = round((sov + (net + 100) / 2) / 2, 2)
        
        exec_kpi_rows.extend([
            {"KPI": f"{b} Brand Health Score", "Value": brand_health, "Status": get_brand_health_status(brand_health)},
            {"KPI": f"{b} Customer Satisfaction Index (CSAT)", "Value": csat, "Status": get_brand_health_status(csat)},
            {"KPI": f"{b} Competitive Position Score", "Value": comp_score, "Status": get_brand_health_status(comp_score)}
        ])
        
    # Data Quality and Pipeline health (general operational stats)
    dq_score = op_metrics["data_completeness"]
    ph_score = op_metrics["pipeline_health"]
    exec_kpi_rows.extend([
        {"KPI": "Data Quality Score (Completeness)", "Value": dq_score, "Status": get_data_quality_status(dq_score)},
        {"KPI": "Pipeline Health Status", "Value": ph_score, "Status": get_pipeline_health_status(ph_score)}
    ])
    
    exec_kpis = pd.DataFrame(exec_kpi_rows)
    exec_kpi_file = os.path.join(reports_dir, "executive_kpis.csv")
    exec_kpis.to_csv(exec_kpi_file, index=False, encoding="utf-8")
    logger.info(f"Saved Executive KPIs to {exec_kpi_file}")

    # 9. Generate Flat KPI Summary (Key-Value format for single card visualization imports)
    kpi_summary_rows = []
    
    # Net Sentiment KPI for all brands
    for idx, b_metrics in enumerate(brand_metrics_list):
        b = b_metrics["brand_name"]
        val = b_metrics["net_sentiment"]
        kpi_summary_rows.append({
            "KPI_Name": "Net Sentiment Score",
            "Dimension": b,
            "KPI_Value": val,
            "KPI_Target": NET_SENTIMENT_TARGET,
            "KPI_Status": get_kpi_status(val, NET_SENTIMENT_TARGET)
        })
        
    # Completeness KPI
    kpi_summary_rows.append({
        "KPI_Name": "Data Completeness Rate",
        "Dimension": "System",
        "KPI_Value": op_metrics["data_completeness"],
        "KPI_Target": DATA_COMPLETENESS_TARGET,
        "KPI_Status": get_kpi_status(op_metrics["data_completeness"], DATA_COMPLETENESS_TARGET)
    })
    
    # Pipeline Health KPI
    kpi_summary_rows.append({
        "KPI_Name": "Pipeline Health",
        "Dimension": "Database",
        "KPI_Value": op_metrics["pipeline_health"],
        "KPI_Target": PIPELINE_HEALTH_TARGET,
        "KPI_Status": get_kpi_status(op_metrics["pipeline_health"], PIPELINE_HEALTH_TARGET)
    })
    
    kpi_summary = pd.DataFrame(kpi_summary_rows)
    kpi_summary_file = os.path.join(reports_dir, "kpi_summary.csv")
    kpi_summary.to_csv(kpi_summary_file, index=False, encoding="utf-8")
    logger.info(f"Saved KPI Summary to {kpi_summary_file}")

    # 10. Generate Star Schema Exports under exports/
    logger.info("Generating relational Power BI Star Schema dimensions & facts...")
    generate_star_schema(results_df, df_pos_annotated, df_neg_annotated, exports_dir)

    logger.info("==========================================")
    logger.info("Phase 6 BI Metrics Pipeline Completed Successfully!")
    logger.info("==========================================")

if __name__ == "__main__":
    run_bi_pipeline()
