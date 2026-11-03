# KPI Definitions and Configurations

# 1. KPI Target Standards
NET_SENTIMENT_TARGET = 50.0       # Target Net Sentiment Score (%)
DATA_COMPLETENESS_TARGET = 95.0   # Target Data Completeness (%)
PIPELINE_HEALTH_TARGET = 90.0     # Target Pipeline Success Rate (%)
CSAT_TARGET = 75.0                # Target Customer Satisfaction Index (%)
BRAND_HEALTH_TARGET = 70.0        # Target Brand Health Score (%)
COMPETITIVE_POSITION_TARGET = 60.0 # Target Competitive Position Score (%)

# 2. KPI Status Resolvers
def get_kpi_status(value: float, target: float) -> str:
    """
    Resolves standard KPI status compared to targets.
    """
    ratio = value / target if target != 0 else 0.0
    if ratio >= 1.1:
        return "Outstanding"
    elif ratio >= 0.9:
        return "On Target"
    elif ratio >= 0.7:
        return "Below Target"
    else:
        return "Critical"

def get_brand_health_status(score: float) -> str:
    """
    Categorizes the Brand Health Score.
    """
    if score >= 80.0:
        return "Excellent"
    elif score >= 60.0:
        return "Good"
    elif score >= 40.0:
        return "Fair"
    else:
        return "Critical"

def get_data_quality_status(completeness: float) -> str:
    """
    Categorizes the Data Quality Score.
    """
    if completeness >= 95.0:
        return "Excellent"
    elif completeness >= 85.0:
        return "Good"
    elif completeness >= 70.0:
        return "Fair"
    else:
        return "Critical"

def get_pipeline_health_status(success_rate: float) -> str:
    """
    Categorizes the Pipeline Health status.
    """
    if success_rate >= 90.0:
        return "Healthy"
    elif success_rate >= 75.0:
        return "Degraded"
    else:
        return "Critical"
