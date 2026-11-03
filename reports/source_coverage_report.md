# Source Coverage Report: Skincare Competitor Intelligence

This report evaluates whether **Reddit** alone provides sufficient customer coverage for competitor intelligence on Indian D2C cosmetics brands (Mamaearth vs. Minimalist) and proposes supplemental channels.

---

## 1. Reddit Discussion Volume & Growth Potential

### Estimated Reddit Discussion Volume
* Reddit skincare discussion is concentrated in dedicated forums such as `r/IndianSkincareAddicts` (over 150k members) and general forums like `r/SkincareAddiction` or `r/IndianBeautyDeals`.
* Monthly posting frequency for terms related to Mamaearth and Minimalist averages **200–500 threads** combined.
* Reddit comments are highly interactive, with popular posts attracting **50 to 200 comments** discussing product side effects, comparisons, and skin routines.

### Dataset Growth Potential
* **Initial Collection**: Running an expanded search on target subreddits can yield **1,000–3,000 unique posts** and **5,000–15,000 comments** spanning 3 years of historical discussions.
* **Monthly Accrual**: Once initial scraping is done, a monthly pipeline can fetch **100–300 new posts** and **1,000–2,000 comments** to maintain fresh data.

---

## 2. Limitations of Reddit-Only Analysis

While Reddit is excellent for qualitative, unbiased discussions, it introduces several biases:

1. **Selection Bias (Demographics)**: Reddit users in Indian skincare subreddits skew younger, urban, English-speaking, and technologically savvy. They do not represent the general mass-market audience of India, particularly Tier 2 and Tier 3 cities where Mamaearth has high sales volumes.
2. **Ingredient-Conscious Bias**: Subreddits like `r/IndianSkincareAddicts` are highly critical of synthetic fillers, fragrance, and generic marketing. This community is naturally biased in favor of **Minimalist** (which focuses on active ingredients) and highly critical of **Mamaearth** (botanical/onion series). It does not represent general consumer purchasing behaviors.
3. **Sparse Rating/Transaction Context**: Reddit posts lack verified purchase statuses and star ratings, making it difficult to link discussions directly to overall customer satisfaction rates.
4. **Scarcity of Product Range Coverage**: Discursive threads focus heavily on a few viral products (e.g. Minimalist Niacinamide, Mamaearth Onion Shampoo), while less controversial items receive zero discussion.

---

## 3. Recommended Future Data Sources

To build a fully representative, multi-dimensional Competitor Intelligence Engine, we recommend integrating the following platforms:

| Data Source | Customer Demographic | Coverage Type | Advantages | Challenges |
| :--- | :--- | :--- | :--- | :--- |
| **Amazon India Reviews** | General mass-market, national coverage. | Verified purchases, structured 1-5 ratings. | Captures general consumer sentiment, large volumes, covers all products. | Aggressive anti-scraping blocks, require proxy/scraping rotation. |
| **Nykaa Reviews** | Skincare/beauty-specific buyers, female-skewed. | Star ratings, buyer profiles (skin type, age). | Rich metadata (e.g., skin type: "dry", "oily"), high trust. | Dynamic rendering, closed API. |
| **Product Review Sites (e.g., Mouthshut)** | General consumers. | Descriptive text reviews, overall satisfaction scores. | Captures long-form complaints and experiences. | Lower posting volume, older demographic. |
| **App Store Reviews (Google Play / iOS App Store)** | Mobile app shoppers. | Brief usability and purchase complaints. | Captures app-specific issues, logistics, and loyalty feedback. | Limited to users shopping via the brand apps. |

---

## 4. Conclusion & Recommendation

* **Current Status**: Reddit is a **highly valuable** channel for capturing unfiltered product critiques, comparative ingredient discussions, and dermatologist-adjacent advice. It serves as an excellent starting point for NLP model training.
* **Next Steps**: For Phase 3, we should proceed with the upgraded Reddit pipeline to secure our baseline dataset. However, for a production-grade competitive benchmark, we must schedule integrations for **Amazon India** and **Nykaa** scraping modules.
