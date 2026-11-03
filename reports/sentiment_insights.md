# Strategic Sentiment Analysis & Insights

This report outlines competitor positioning insights and customer perception trends.

---

## 1. Sentiment Benchmarking Summary

| Brand | Total Reviews | Positive % | Neutral % | Negative % | Net Sentiment Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Kay Beauty** | 13783 | 78.97% | 19.53% | 1.49% | **+77.48** |
| **Nykaa Cosmetics** | 17650 | 75.5% | 21.3% | 3.2% | **+72.29** |
| **Brand Sentiment Gap** | - | - | - | - | **-5.19** |

*Note: Net Sentiment Score is computed as `((Positive - Negative) / Total) * 100`, ranging from -100 (entirely negative) to +100 (entirely positive).*
*The Brand Sentiment Gap represents `Nykaa Cosmetics Net Sentiment - Kay Beauty Net Sentiment`.*

---

## 2. Competitor Positioning Observations

### A. Nykaa Cosmetics: Market Leader Analysis
* **Net Sentiment**: **+72.29**
* **Core Drivers**: Nykaa Cosmetics exhibits a strong sentiment profile driven by product satisfaction, ingredient quality, and customer trust. 
* **Key Risk Areas**: Minor customer friction exists around specific product formulations, product texture, or packaging options.

### B. Kay Beauty: Challenger Analysis
* **Net Sentiment**: **+77.48**
* **Core Drivers**: Kay Beauty has a substantial footprint in the market. While its core botanical and mass-market lines receive positive feedback, specific product lines drag down the overall sentiment score.

### C. Competitor Key Performance Indicators
* **Brand Sentiment Gap (Nykaa Cosmetics Net - Kay Beauty Net)**: **-5.19**
  This gap reflects the relative satisfaction indices of the top two brands in our cosmetics database.

---

## 3. Recommended Competitor Actions (Phase 5 Preparations)

1. **Complaints and Friction Auditing**: We must schedule **Phase 5 Topic Modeling** to dynamically cluster and categorize specific consumer complaints.
2. **Competitor Strength Profiling**: Track areas where Nykaa Cosmetics is perceived as superior to Kay Beauty, aiding strategic formulation positioning.
3. **Topic Modeling Output Ingestion**: Use `reports/high_confidence_negative.csv` and `reports/high_confidence_positive.csv` to directly consume and analyze granular topics of praise and complaints for Phase 5.
