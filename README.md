# Brand & Competitor Intelligence Engine - Phase 1

An end-to-end Python pipeline designed to ingest, monitor, and preprocess customer feedback and online discussions regarding D2C brands. Phase 1 focuses on extracting raw posts and comments from Reddit (via PRAW), persisting data to an SQLite relational database, exporting raw CSV files, and preprocessing text in-memory for downstream NLP and analytics tasks.

---

## Folder Structure

```text
brand-intelligence-engine/
│
├── data/                       # CSV backups of raw & preprocessed data
├── database/                   # SQLite database directory
├── logs/                       # Application execution log files
├── notebooks/                  # Directory for analysis notebooks (future phases)
├── src/                        # Core application code
│   ├── data_collection/        # Reddit PRAW ingestion scripts
│   │   ├── __init__.py
│   │   └── reddit_collector.py
│   ├── preprocessing/          # Text cleaner, lemmatizer, and normalizer
│   │   ├── __init__.py
│   │   └── text_preprocessing.py
│   ├── sentiment/              # Placeholder for future NLP phase
│   ├── topic_modeling/         # Placeholder for future topic modeling phase
│   ├── recommendations/        # Placeholder for recommendation engine phase
│   └── utils/                  # Shared configurations, database connection, and logger
│       ├── __init__.py
│       ├── config.py
│       ├── database_helper.py
│       └── logger.py
├── dashboard/                  # Streamlit dashboards (future phases)
├── tests/                      # Unit test suites
│   ├── __init__.py
│   ├── test_database.py
│   └── test_preprocessing.py
├── .env.example                # Sample environment variables
├── .gitignore                  # Git untracked pattern matching
├── requirements.txt            # Python package dependencies
├── pipeline.py                 # End-to-end execution orchestrator
└── README.md                   # Setup and execution guide (this file)
```

---

## Features

1. **Reddit API Ingestion (PRAW)**:
   - Queries posts containing specified search terms for targets (e.g., Mamaearth vs Minimalist).
   - Fetches comments associated with relevant submissions.
   - Fallback offline/mock mode allows running the pipeline and validating code execution without requiring actual Reddit API credentials.
2. **SQLite Relational Schema**:
   - Strictly enforces foreign keys (e.g., matching comments to posts, and posts/comments to brands).
   - Keeps SQLite as a **raw-data-only** store.
   - Monitors pipeline executions via a dedicated `collection_runs` logging table.
3. **Multi-Brand Disambiguation**:
   - Detects brand mentions in titles and bodies of fetched posts.
   - Resolves ownership based on mention frequency, logging co-mention events.
4. **Structured Preprocessing**:
   - Cleans text: lowercases, strips URLs, removes non-alphanumeric special characters.
   - Performs tokenization, filters English stopwords (via NLTK), and lemmatizes words (via WordNet).
5. **Unified Logging**:
   - Dual handlers log formatted, detailed traces to both standard output (console) and a rotating file at `logs/project.log`.

---

## Setup Instructions

### 1. Clone/Open the Project
Open the project directory in your terminal:
```bash
cd Brand_Competitor_Intelligence_engine
```

### 2. Install Dependencies
Install the required libraries:
```bash
pip install -r requirements.txt
```

### 3. Environment Configurations
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your Reddit API credentials:
* Get your client credentials from [Reddit Apps Preferences](https://www.reddit.com/prefs/apps). Create a script type application.
```ini
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=brand-intel-engine/1.0 by /u/yourusername
```
*If credentials are left empty or invalid, the collector will automatically fall back to **Mock Mode** using realistic pre-coded data so you can still run the entire system.*

---

## Example Execution Commands

### 1. Run the Pipeline
Execute the full collection, database ingestion, raw CSV export, and preprocessing preview:
```bash
python pipeline.py
```
Upon running, you should expect:
1. `database/brand_intelligence.db` will be created with populated schemas and raw records.
2. CSV files will be generated under `data/`:
   - `data/raw_posts.csv` & `data/raw_comments.csv` (raw data backups)
   - `data/preprocessed_posts.csv` & `data/preprocessed_comments.csv` (preprocessed text files with a `clean_text` column)
3. Running logs will be written to `logs/project.log`.
4. Preprocessing comparison previews will display in the console.

### 2. Run the Unit Test Suite
To verify the implementation:
```bash
python -m pytest tests/
```
Tests are completely independent and use a fast in-memory SQLite database (`:memory:`), ensuring they do not affect local files.
