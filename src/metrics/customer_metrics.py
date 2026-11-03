import pandas as pd
from typing import Dict, Any, List

def calculate_customer_experience_metrics(df_pos: pd.DataFrame, df_neg: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes Customer Experience KPIs: top praise/complaints and concentrations.
    """
    metrics = {
        "top_complaint_category": "None",
        "top_praise_category": "None",
        "complaint_concentration": 0.0,
        "praise_concentration": 0.0
    }
    
    # 1. Negative complaints concentration
    if not df_neg.empty:
        valid_neg = df_neg[df_neg["mapped_topic"] != "Unmapped"]
        if not valid_neg.empty:
            counts = valid_neg["mapped_topic"].value_counts()
            top_complaint = counts.index[0]
            top_count = counts.iloc[0]
            total_complaints = len(valid_neg)
            
            metrics["top_complaint_category"] = top_complaint
            metrics["complaint_concentration"] = round((top_count / total_complaints * 100), 2)
            
    # 2. Positive praise concentration
    if not df_pos.empty:
        valid_pos = df_pos[df_pos["mapped_topic"] != "Unmapped"]
        if not valid_pos.empty:
            counts = valid_pos["mapped_topic"].value_counts()
            top_praise = counts.index[0]
            top_count = counts.iloc[0]
            total_praise = len(valid_pos)
            
            metrics["top_praise_category"] = top_praise
            metrics["praise_concentration"] = round((top_count / total_praise * 100), 2)
            
    return metrics


def generate_risk_opportunity_scorecard(df_pos: pd.DataFrame, df_neg: pd.DataFrame) -> pd.DataFrame:
    """
    Generates a Risk & Opportunity Scorecard for business decision making.
    Columns: Type, Topic, Frequency, Brand, Priority
    """
    records = []
    
    # 1. Process Risks (from complaints/negatives)
    if not df_neg.empty:
        valid_neg = df_neg[df_neg["mapped_topic"] != "Unmapped"]
        if not valid_neg.empty:
            grouped = valid_neg.groupby(["mapped_topic", "brand"]).size().reset_index(name="frequency")
            for _, row in grouped.iterrows():
                topic = row["mapped_topic"]
                brand = row["brand"]
                freq = int(row["frequency"])
                
                # Determine Priority
                if freq >= 3:
                    priority = "High"
                elif freq >= 2:
                    priority = "Medium"
                else:
                    priority = "Low"
                    
                records.append({
                    "Type": "Risk",
                    "Topic": topic,
                    "Frequency": freq,
                    "Brand": brand,
                    "Priority": priority
                })
                
    # 2. Process Opportunities (from praise/positives)
    if not df_pos.empty:
        valid_pos = df_pos[df_pos["mapped_topic"] != "Unmapped"]
        if not valid_pos.empty:
            grouped = valid_pos.groupby(["mapped_topic", "brand"]).size().reset_index(name="frequency")
            for _, row in grouped.iterrows():
                topic = row["mapped_topic"]
                brand = row["brand"]
                freq = int(row["frequency"])
                
                # Determine Priority
                if freq >= 3:
                    priority = "High"
                elif freq >= 2:
                    priority = "Medium"
                else:
                    priority = "Low"
                    
                records.append({
                    "Type": "Opportunity",
                    "Topic": topic,
                    "Frequency": freq,
                    "Brand": brand,
                    "Priority": priority
                })
                
    df_scorecard = pd.DataFrame(records)
    if df_scorecard.empty:
        df_scorecard = pd.DataFrame(columns=["Type", "Topic", "Frequency", "Brand", "Priority"])
    else:
        # Sort by Type, Priority descending, Frequency descending
        priority_map = {"High": 3, "Medium": 2, "Low": 1}
        df_scorecard["p_val"] = df_scorecard["Priority"].map(priority_map)
        df_scorecard = df_scorecard.sort_values(by=["Type", "p_val", "Frequency"], ascending=[True, False, False]).drop(columns=["p_val"])
        
    return df_scorecard
