import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
from src.utils.logger import logger

# Set default theme
pio.templates.default = "plotly_white"

def generate_topic_visualizations(pain_df: pd.DataFrame, praise_df: pd.DataFrame, figures_dir: str) -> None:
    """
    Generates interactive Plotly HTML charts for Phase 5 VoC topic analysis.
    
    Args:
        pain_df (pd.DataFrame): Customer pain points dataframe.
        praise_df (pd.DataFrame): Customer praise points dataframe.
        figures_dir (str): Output folder for HTML charts.
    """
    logger.info("Generating Topic Modeling Visualizations...")
    os.makedirs(figures_dir, exist_ok=True)

    # Color palette
    colors_complaints = "#ff3333"  # Soft red
    colors_praise = "#33cc66"      # Soft green
    
    brand_colors = {
        "Mamaearth": "#99cc33",
        "Minimalist": "#222222"
    }

    # 1. Top Complaint Categories (Bar Chart)
    if not pain_df.empty:
        comp_agg = pain_df.groupby("topic")["frequency"].sum().reset_index()
        fig_complaints = px.bar(
            comp_agg,
            x="topic",
            y="frequency",
            title="Top Customer Complaint Categories",
            labels={"topic": "Complaint Theme", "frequency": "Complaint Count"},
            color_discrete_sequence=[colors_complaints]
        )
        pio.write_html(fig_complaints, os.path.join(figures_dir, "top_complaints.html"))
    else:
        logger.warning("Pain points dataframe is empty. Skipping top_complaints.html")

    # 2. Top Praise Categories (Bar Chart)
    if not praise_df.empty:
        praise_agg = praise_df.groupby("topic")["frequency"].sum().reset_index()
        fig_praise = px.bar(
            praise_agg,
            x="topic",
            y="frequency",
            title="Top Customer Praise Categories",
            labels={"topic": "Praise Theme", "frequency": "Praise Count"},
            color_discrete_sequence=[colors_praise]
        )
        pio.write_html(fig_praise, os.path.join(figures_dir, "top_praise.html"))
    else:
        logger.warning("Praise points dataframe is empty. Skipping top_praise.html")

    # Combine dataframes for distribution charts
    combined_list = []
    if not pain_df.empty:
        pain_copy = pain_df.copy()
        pain_copy["type"] = "Complaint"
        combined_list.append(pain_copy)
    if not praise_df.empty:
        praise_copy = praise_df.copy()
        praise_copy["type"] = "Praise"
        combined_list.append(praise_copy)

    if not combined_list:
        logger.warning("No data available to generate distribution charts.")
        return

    combined_df = pd.concat(combined_list, ignore_index=True)

    # 3. Topic Distribution by Brand (Grouped Bar Chart)
    brand_dist = combined_df.groupby(["brand", "topic"])["frequency"].sum().reset_index()
    fig_brand = px.bar(
        brand_dist,
        x="topic",
        y="frequency",
        color="brand",
        barmode="group",
        title="Topic Frequency Distribution by Brand",
        labels={"topic": "Topic Category", "frequency": "Count", "brand": "Brand"},
        color_discrete_map=brand_colors
    )
    pio.write_html(fig_brand, os.path.join(figures_dir, "topic_dist_brand.html"))

    # 4. Topic Distribution by Source (Grouped Bar Chart)
    source_dist = combined_df.groupby(["source", "topic"])["frequency"].sum().reset_index()
    fig_source = px.bar(
        source_dist,
        x="topic",
        y="frequency",
        color="source",
        barmode="group",
        title="Topic Frequency Distribution by Data Source",
        labels={"topic": "Topic Category", "frequency": "Count", "source": "Source Platform"}
    )
    pio.write_html(fig_source, os.path.join(figures_dir, "topic_dist_source.html"))

    # 5. Complaint vs Praise Comparison (Stacked Bar Chart per Brand)
    cvp_dist = combined_df.groupby(["brand", "type"])["frequency"].sum().reset_index()
    fig_cvp = px.bar(
        cvp_dist,
        x="brand",
        y="frequency",
        color="type",
        title="Praise vs. Complaint Volume Comparison",
        labels={"brand": "Brand", "frequency": "Volume Count", "type": "Feedback Type"},
        color_discrete_map={"Praise": colors_praise, "Complaint": colors_complaints}
    )
    pio.write_html(fig_cvp, os.path.join(figures_dir, "complaint_vs_praise.html"))

    logger.info("Topic Modeling Visualizations successfully exported to HTML.")
