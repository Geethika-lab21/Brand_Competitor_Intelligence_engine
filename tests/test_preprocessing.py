import pytest
import pandas as pd
from src.preprocessing.text_preprocessing import TextPreprocessor

@pytest.fixture
def preprocessor() -> TextPreprocessor:
    return TextPreprocessor()

def test_remove_urls(preprocessor: TextPreprocessor) -> None:
    text_with_url = "Check this link https://example.com/test for more info."
    cleaned = preprocessor.remove_urls(text_with_url)
    assert "https://example.com/test" not in cleaned
    assert "Check this link  for more info." in cleaned

    text_with_www = "Visit www.test-site.org for details."
    cleaned_www = preprocessor.remove_urls(text_with_www)
    assert "www.test-site.org" not in cleaned_www
    assert "Visit  for details." in cleaned_www

def test_remove_special_characters(preprocessor: TextPreprocessor) -> None:
    text_with_specials = "Hello, World! @Minimalist 100% #serum."
    cleaned = preprocessor.remove_special_characters(text_with_specials)
    assert "Hello World Minimalist 100 serum" in cleaned
    assert "@" not in cleaned
    assert "%" not in cleaned
    assert "#" not in cleaned

def test_remove_stopwords(preprocessor: TextPreprocessor) -> None:
    tokens = ["this", "is", "a", "good", "shampoo", "for", "hair"]
    filtered = preprocessor.remove_stopwords(tokens)
    # 'this', 'is', 'a', 'for' are standard English stopwords
    assert "this" not in filtered
    assert "is" not in filtered
    assert "good" in filtered
    assert "shampoo" in filtered
    assert "hair" in filtered

def test_lemmatize_text(preprocessor: TextPreprocessor) -> None:
    tokens = ["shampoos", "products", "serums", "brands"]
    lemmatized = preprocessor.lemmatize_text(tokens)
    assert "shampoo" in lemmatized
    assert "product" in lemmatized
    assert "serum" in lemmatized
    assert "brand" in lemmatized

def test_preprocess_text_pipeline(preprocessor: TextPreprocessor) -> None:
    raw_text = "I love using Minimalist's 10% Niacinamide serum! It is amazing: https://beminimalist.co"
    processed = preprocessor.preprocess_text(raw_text)
    # Preprocessing should:
    # 1. Lowercase: "i love using minimalist's 10% niacinamide serum! it is amazing: https://beminimalist.co"
    # 2. URL removal: "i love using minimalist's 10% niacinamide serum! it is amazing: "
    # 3. Special char removal: "i love using minimalists 10 niacinamide serum it is amazing "
    # 4. Tokenization: ["i", "love", "using", "minimalists", "10", "niacinamide", "serum", "it", "is", "amazing"]
    # 5. Stopwords removal: ["love", "using", "minimalists", "10", "niacinamide", "serum", "amazing"] (since 'i', 'it', 'is' are stopwords)
    # 6. Lemmatization: "love using minimalist serum amazing" (or similar depending on lemmatization)
    assert "love" in processed
    assert "niacinamide" in processed
    assert "serum" in processed
    assert "https" not in processed

def test_preprocess_text_edge_cases(preprocessor: TextPreprocessor) -> None:
    assert preprocessor.preprocess_text("") == ""
    assert preprocessor.preprocess_text("   ") == ""
    assert preprocessor.preprocess_text(None) == "" # type: ignore
    assert preprocessor.preprocess_text("!!! @@@ ###") == ""

def test_preprocess_dataframe(preprocessor: TextPreprocessor) -> None:
    df = pd.DataFrame({
        "title": ["Great sunscreen", "Terrible shampoo"],
        "body": ["Minimalist sunscreen is wonderful.", "Mamaearth onion shampoo caused hairfall."]
    })
    
    # Test single column preprocessing
    df_clean_body = preprocessor.preprocess_dataframe(df, text_columns="body")
    assert "clean_text" in df_clean_body.columns
    assert "sunscreen" in df_clean_body.loc[0, "clean_text"]
    assert "shampoo" in df_clean_body.loc[1, "clean_text"]

    # Test multi-column concatenation preprocessing
    df_concat = preprocessor.preprocess_dataframe(df, text_columns=["title", "body"])
    assert "clean_text" in df_concat.columns
    assert "great" in df_concat.loc[0, "clean_text"]
    assert "sunscreen" in df_concat.loc[0, "clean_text"]
    assert "terrible" in df_concat.loc[1, "clean_text"]
