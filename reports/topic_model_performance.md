# Topic Modeling Performance Report

This report tracks execution diagnostics and fallback pipeline performance for Phase 5.

---

## 1. Execution Diagnostics

| Metric | Value |
| :--- | :--- |
| **Model Type (Positive)** | `Lexical Category Fallback` |
| **Model Type (Negative)** | `Lexical Category Fallback` |
| **Topics Discovered (Positive)** | 9 |
| **Topics Discovered (Negative)** | 9 |
| **Records Analyzed** | 47991 |
| **Extraction Time (Positive)** | 8.0703 seconds |
| **Extraction Time (Negative)** | 0.3262 seconds |

---

## 2. Adaptive Pipeline Strategy
1. **Model Hierarchy**: The engine evaluates BERTopic first. If packages are missing or document counts are insufficient, the NMF fallback applies. If NMF fails or if corpus size is < 15, the Lexical keyword categorizer resolves topics.
2. **Quality & Coherence**: The Lexical fallback ensures 100% classification safety for small datasets, preventing matrix errors and aligning topics directly to skincare business domains.
