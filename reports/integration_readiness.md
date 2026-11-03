# Integration Readiness Report: Nykaa Dataset

This report assesses the compatibility of the Nykaa cosmetics product reviews dataset with the existing `CSVSource` data ingestion pipeline.

## Schema Mapping Document

The following mapping must be applied to align the Nykaa dataset with the standardized Brand Intelligence schema:

```text
review_id      -> source_record_id
brand_name     -> brand
review_title   -> title
review_text    -> text
review_rating  -> rating
review_date    -> created_at
author         -> author
```

## Schema Mapping Validation

The table below documents the mapping between the Nykaa dataset columns and the standardized Brand Intelligence schema fields:

| Standardized Field | Target Column (Nykaa) | Resolved by CSVSource? | Matching Candidate Found | Notes |
|---|---|---|---|---|
| `source_record_id` | `review_id` | **Yes** | `review_id` | Resolved automatically via candidates list. |
| `brand` | `brand_name` | **Yes** | `brand_name` | Resolved automatically in brand filter code. |
| `title` | `review_title` | **Yes** | `review_title` | Resolved automatically via candidates list. |
| `text` | `review_text` | **Yes** | `review_text` | Resolved automatically via candidates list. |
| `rating` | `review_rating` | **No** | None | **Action Required:** `review_rating` is not in the default candidate list `["rating", "score", "stars", "star_rating", "rating_value"]`. `CSVSource` will fail to extract ratings unless explicitly mapped. |
| `author` | `author` | **Yes** | `author` | Resolved automatically via candidates list. |
| `created_at` | `review_date` | **Yes** | `review_date` | Resolved automatically via candidates list. |

## Compatibility & Gaps Analysis

1. **Rating Field Resolution Gap**:
   - `CSVSource` does not include `"review_rating"` as a candidate for `"rating"`.
   - **Resolution**: Use the `column_mapping` parameter during source loading or update the candidate list in `CSVSource` to include `"review_rating"`. E.g.:
     ```python
     column_mapping = {"rating": "review_rating"}
     ```

2. **Date Parsing Integrity**:
   - The dates are formatted in the Nykaa dataset (e.g., `2021-01-23`). `CSVSource` parses dates using `pd.to_datetime(val).timestamp()`.
   - **Validation**: Testing on a subset of dates confirmed that `CSVSource` successfully parses these values to standard UNIX epoch timestamps.

3. **Data Volume Considerations**:
   - The Nykaa dataset contains **61,284** records.
   - Filtering specifically for **Mamaearth** (0 reviews) and **Minimalist** (0 reviews) results in a total subset of **0** reviews.
   - **Note**: Neither Mamaearth nor Minimalist exists in this Nykaa cosmetics dataset. To ingest Nykaa reviews, we must configure the pipeline to target the brands actually present in the dataset (e.g., "Olay", "L'Oreal Paris", "Maybelline New York", "Nykaa Cosmetics", etc.).

## Proposed Integration Actions

1. **Custom Column Mapping**:
   When invoking `CSVSource.fetch_data()`, configure `column_mapping` to resolve the `rating` column:
   ```python
   csv_source.fetch_data(
       brand_name="Olay", 
       csv_path="data/nyka_top_brands_cosmetics_product_reviews.csv",
       column_mapping={"rating": "review_rating"}
   )
   ```
2. **Data Cleanliness**:
   - Ensure null text values in `review_text` are filtered out. (This is already handled by `CSVSource` which skips records with empty text).
   - Ensure the parsed timestamp falls back to the current time or epoch if parsing fails.
