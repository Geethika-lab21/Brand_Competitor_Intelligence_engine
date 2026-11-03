# Source Readiness Evaluation Report

This report evaluates and compares **Reddit**, **Amazon**, **Nykaa**, and **Kaggle** datasets as data feeds for the D2C Skincare Brand Competitor Intelligence Engine.

---

## 1. Platform Source Comparison Matrix

| Evaluation Criteria | Reddit API (PRAW) | Amazon India Reviews | Nykaa Reviews | Kaggle Review Datasets |
| :--- | :--- | :--- | :--- | :--- |
| **Data Volume** | Medium (100–500 posts/mo) | High (1,000–10,000 reviews) | High (500–5,000 reviews) | High (Static, pre-packaged) |
| **Ease of Access** | Medium (API approval pending) | Hard (Anti-scraping, dynamic) | Hard (Closed API, dynamic) | Very Easy (Direct CSV download) |
| **Data Quality** | High (Unbiased, organic) | Medium (Verified & fake reviews) | High (Specific to skincare buyers) | High (Cleaned but static) |
| **Acquisition Cost** | Free (Reddit Developer API) | High (Proxy rotation costs) | High (Proxy/Scraping scripts) | Free (Open datasets) |
| **Sentiment Suitability** | High (Captures nuanced critiques) | Very High (Explicit star ratings) | Very High (Explicit star ratings) | High (Aids testing baseline) |
| **Topic Modeling (BERTopic)** | Very High (Long-form discussions) | High (Specific product reviews) | High (Product efficacy details) | Medium (Limited context range) |

---

## 2. In-Depth Evaluation & Insights

### A. Reddit (API Access)
* **Status**: **Pending API Approval**.
* **Role**: Reddit is valuable for capturing detailed consumer feedback, side-effects, pricing debates, and organic competitor comparisons. It skewing towards Skincare Enthusiasts.
* **BERTopic / Sentiment Suitability**: Excellent for topic modeling because of long-form, discursive post bodies.

### B. Amazon India Reviews
* **Status**: **Scraper Required (Future Integration)**.
* **Role**: The main driver for volume and ratings-based sentiment analysis. Reviews are tied to verified transactions and represent mass-market consumer satisfaction rates.
* **BERTopic / Sentiment Suitability**: Highly suitable for sentiment model validation, since raw star ratings provide an instant ground-truth label (e.g., 5-star is positive, 1-star is negative).

### C. Nykaa Reviews
* **Status**: **Scraper Required (Future Integration)**.
* **Role**: Captures niche beauty buyers. Reviews are accompanied by vital user demographics (e.g. skin type: dry/oily/sensitive, age range), offering demographic-based targeting.
* **BERTopic / Sentiment Suitability**: Ideal for product-specific sentiment (e.g. tracking how dry-skin users perceive Mamaearth moisturizer vs. oily-skin users).

### D. Kaggle / Local CSV Datasets
* **Status**: **Ready (Via CSV Ingestion Framework)**.
* **Role**: Serves as a vital baseline for early modeling and pipeline testing. It provides large volumes of text reviews immediately without network API blocks or scrapers.
* **BERTopic / Sentiment Suitability**: Very high for testing classification models, although datasets are static and lack real-time freshness.

---

## 3. Recommended Source Strategy

To bypass Reddit API bottlenecks and scale competitive intelligence immediately, we recommend a **Hybrid Multi-Source Architecture**:

1. **Phase 4 Baseline**: Initialize using our new `CSVSource` by loading exported Kaggle/Amazon review datasets (located under `data/`). This unblocks development of the Sentiment Engine without architectural dependency on Reddit.
2. **Phase 5 Topic Modeling Integration**: Run the `RedditSource` once developer app approval is secured to enrich the corpus with conversational, comparative discussions.
3. **Production Deployment**: Schedule cron-based scraping pipelines for Amazon and Nykaa to ingest live verified reviews.
