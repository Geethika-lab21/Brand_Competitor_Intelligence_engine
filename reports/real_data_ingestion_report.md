# Real Data Ingestion Diagnostics Report

This diagnostics report summarizes the results of ingesting the Nykaa product reviews dataset into the Beauty & Cosmetics Brand Intelligence database.

## 1. Ingestion Executive Summary

* **Date Ingested**: 2026-06-11 12:14:20
* **Database Path**: `database/brand_intelligence.db`
* **Total Reviews Standardized & Ingested**: 61,275
* **Skipped (Empty reviews)**: 0
* **Ingestion Runtime**: 29.83 seconds
* **Throughput**: 2054.44 records/second
* **Pipeline Status**: **SUCCESS**

## 2. Ingested Brand Distribution

| Brand | Ingested Review Volume | Percentage of Total |
| :--- | :---: | :---: |
| Nykaa Cosmetics | 17,650 | 28.80% |
| Kay Beauty | 13,783 | 22.49% |
| Lakme | 6,997 | 11.42% |
| Maybelline New York | 6,821 | 11.13% |
| Herbal Essences | 6,197 | 10.11% |
| L'Oreal Paris | 4,273 | 6.97% |
| NYX Professional Makeup | 2,954 | 4.82% |
| Nykaa Naturals | 1,426 | 2.33% |
| Nivea | 774 | 1.26% |
| Olay | 399 | 0.65% |
| Colorbar | 1 | 0.00% |

## 3. Coverage Analysis

* **Temporal Date Coverage**: 2013-05-20 to 2022-10-22
* **Data Ingestion Sources**: `nykaa` (100.00% review volume)

## 4. Ingested Schema Missing Values Audit

| Field | Description | Missing Count | Missing % |
| :--- | :--- | :---: | :---: |
| `source_record_id` | Standardized Unique Key | 0 | 0.00% |
| `brand` | Associated Brand Name | 0 | 0.00% |
| `title` | Review Headline | 0 | 0.00% |
| `text` | Cleaned Body Text | 0 | 0.00% |
| `rating` | Numeric Score (1-5) | 1 | 0.00% |
| `author` | Reviewer Username | 0 | 0.00% |
| `created_at` | Epoch Timestamp | 0 | 0.00% |

## 5. Schema Validation & Integrity Checklist

- [x] **Primary Key Uniqueness**: Verified. Zero duplicate `source_record_id` strings found.
- [x] **Foreign Key Integrity**: Verified. All `brand_id` associations resolve correctly to the SQLite `brands` table.
- [x] **Data Type Compatibility**: Verified. Ratings converted to floats and dates converted to UNIX epochs.
- [x] **Null Constraints Safety**: Verified. All skipped records with null text were filtered prior to insertion.
