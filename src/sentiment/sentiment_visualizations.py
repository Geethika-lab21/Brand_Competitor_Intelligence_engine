import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
from src.utils.logger import logger

# Set default theme
pio.templates.default = "plotly_white"

def generate_sentiment_visualizations(df: pd.DataFrame, figures_dir: str) -> None:
    """
    Generates Plotly interactive sentiment charts and saves them as HTML.
    
    Args:
        df (pd.DataFrame): Detailed predictions dataframe containing columns:
            - brand
            - source
            - sentiment_label
            - created_at
        figures_dir (str): Output directory for html figures.
    """
    logger.info("Generating Sentiment Visualizations...")
    os.makedirs(figures_dir, exist_ok=True)
    
    # Standard color maps
    sentiment_colors = {
        "positive": "#33cc66",  # Soft Green
        "neutral": "#999999",   # Cool Gray
        "negative": "#ff3333"   # Soft Red
    }
    brand_colors = {
        "Mamaearth": "#99cc33",
        "Minimalist": "#222222"
    }

    # 1. Sentiment by Brand (Distribution Bar Chart)
    # Count sentiment per brand and calculate percentages
    brand_counts = df.groupby(["brand", "sentiment_label"]).size().reset_index(name="count")
    brand_totals = brand_counts.groupby("brand")["count"].transform("sum")
    brand_counts["percentage"] = (brand_counts["count"] / brand_totals) * 100

    fig_brand = px.bar(
        brand_counts,
        x="brand",
        y="percentage",
        color="sentiment_label",
        barmode="group",
        title="Sentiment Distribution by Brand",
        labels={"percentage": "Percentage (%)", "brand": "Brand", "sentiment_label": "Sentiment"},
        color_discrete_map=sentiment_colors
    )
    pio.write_html(fig_brand, os.path.join(figures_dir, "sentiment_by_brand.html"))

    # 2. Sentiment by Source (Grouped Bar Chart)
    source_counts = df.groupby(["source", "sentiment_label"]).size().reset_index(name="count")
    source_totals = source_counts.groupby("source")["count"].transform("sum")
    source_counts["percentage"] = (source_counts["count"] / source_totals) * 100

    fig_source = px.bar(
        source_counts,
        x="source",
        y="percentage",
        color="sentiment_label",
        barmode="group",
        title="Sentiment Distribution by Data Source",
        labels={"percentage": "Percentage (%)", "source": "Source Platform", "sentiment_label": "Sentiment"},
        color_discrete_map=sentiment_colors
    )
    pio.write_html(fig_source, os.path.join(figures_dir, "sentiment_by_source.html"))

    # 3. Sentiment over Time (Line Chart of Net Sentiment)
    # Convert created_at epoch to datetime year-month
    df_time = df.copy()
    df_time["datetime"] = pd.to_datetime(df_time["created_at"], unit="s")
    df_time["year_month"] = df_time["datetime"].dt.to_period("M").astype(str)
    
    # Calculate monthly Net Sentiment per brand
    monthly_net = []
    grouped_time = df_time.groupby(["year_month", "brand"])
    for (ym, brand), gp in grouped_time:
        tot = len(gp)
        pos = sum(gp["sentiment_label"] == "positive")
        neg = sum(gp["sentiment_label"] == "negative")
        net = ((pos - neg) / tot * 100) if tot > 0 else 0.0
        
        monthly_net.append({
            "year_month": ym,
            "brand": brand,
            "net_sentiment": round(net, 2)
        })
        
    monthly_net_df = pd.DataFrame(monthly_net)
    if not monthly_net_df.empty:
        # Sort chronologically
        monthly_net_df = monthly_net_df.sort_values(by="year_month")
        fig_time = px.line(
            monthly_net_df,
            x="year_month",
            y="net_sentiment",
            color="brand",
            title="Monthly Net Sentiment Trends",
            labels={"year_month": "Month", "net_sentiment": "Net Sentiment Score", "brand": "Brand"},
            color_discrete_map=brand_colors,
            markers=True
        )
        pio.write_html(fig_time, os.path.join(figures_dir, "sentiment_over_time.html"))

    # 4. Net Sentiment Comparison (Bar Chart)
    net_overall = []
    for brand in df["brand"].unique():
        brand_df = df[df["brand"] == brand]
        tot = len(brand_df)
        pos = sum(brand_df["sentiment_label"] == "positive")
        neg = sum(brand_df["sentiment_label"] == "negative")
        net = ((pos - neg) / tot * 100) if tot > 0 else 0.0
        net_overall.append({
            "brand": brand,
            "net_sentiment": round(net, 2)
        })
        
    net_overall_df = pd.DataFrame(net_overall)
    if not net_overall_df.empty:
        fig_net = px.bar(
            net_overall_df,
            x="brand",
            y="net_sentiment",
            title="Competitor Net Sentiment Benchmarking",
            labels={"net_sentiment": "Net Sentiment Score", "brand": "Brand"},
            color="brand",
            color_discrete_map=brand_colors
        )
        fig_net.update_layout(showlegend=False)
        pio.write_html(fig_net, os.path.join(figures_dir, "net_sentiment_comparison.html"))

    logger.info("Sentiment Visualizations successfully exported to HTML.")
