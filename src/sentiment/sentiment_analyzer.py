import time
from typing import Dict, Any, List, Optional
from src.utils.logger import logger

# Try to import transformers for Hugging Face modeling
TRANSFORMERS_AVAILABLE = False
try:
    from transformers import pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning(
        "Hugging Face 'transformers' or 'torch' packages are not available. "
        "Sentiment Analyzer will fall back to Lexicon-based analysis."
    )

class LexiconSentimentAnalyzer:
    """
    Fallback rule-based sentiment classifier using a local skincare-specific lexicon.
    Runs offline without requiring model downloads or heavy deep-learning frameworks.
    """
    
    def __init__(self) -> None:
        # Skincare & customer review specific terminology
        self.positive_lexicon = {
            "good", "great", "excellent", "love", "awesome", "best", "perfect",
            "effective", "amazing", "safe", "recommend", "happy", "glowing",
            "cleared", "improvement", "soothing", "transparent", "gamechanger",
            "hydrated", "brightening", "worth", "smooth", "healed", "nice"
        }
        
        self.negative_lexicon = {
            "bad", "terrible", "worst", "hate", "horrible", "awful", "waste",
            "useless", "breakout", "greasy", "greasiness", "hairfall", "fall",
            "clumps", "ruined", "ghost", "whitecast", "greasy", "acne", "scars",
            "expensive", "irritation", "burning", "redness", "disappointment"
        }

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Calculates simple lexicon counts and outputs a label and confidence score.
        """
        if not text or not isinstance(text, str):
            return {"label": "neutral", "score": 0.0, "confidence": 1.0}
            
        words = re.findall(r"\b\w+\b", text.lower()) if "re" in globals() else text.lower().split()
        
        pos_count = sum(1 for w in words if w in self.positive_lexicon)
        neg_count = sum(1 for w in words if w in self.negative_lexicon)
        
        total = pos_count + neg_count
        if total == 0:
            return {"label": "neutral", "score": 0.0, "confidence": 1.0}
            
        score = (pos_count - neg_count) / total
        
        # Determine label and confidence
        if score > 0.15:
            label = "positive"
            confidence = pos_count / total
        elif score < -0.15:
            label = "negative"
            confidence = neg_count / total
        else:
            label = "neutral"
            confidence = 1.0 - abs(score)
            
        # Standardize score mapping
        score_map = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
        
        return {
            "label": label,
            "score": score_map[label],
            "confidence": round(confidence, 4)
        }

# Inject regex import to helper if needed
import re

class SentimentAnalyzer:
    """
    Sentiment Analyzer using Twitter-RoBERTa model.
    Maintains a robust rule-based fallback if model initialization fails.
    """

    def __init__(self, force_fallback: bool = False) -> None:
        """
        Initializes the Sentiment Analyzer.
        
        Args:
            force_fallback (bool): If True, forces VADER-adjacent lexicon analysis.
        """
        self.model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
        self.classifier = None
        self.fallback_analyzer = LexiconSentimentAnalyzer()
        self.using_fallback = force_fallback
        self.fallback_count = 0
        self.processed_count = 0
        
        if not force_fallback and TRANSFORMERS_AVAILABLE:
            try:
                logger.info(f"Loading Hugging Face sentiment model '{self.model_name}'...")
                # Load pipeline, CPU by default (safe fallback), GPU if cuda exists
                device = 0 if torch.cuda.is_available() else -1
                self.classifier = pipeline(
                    "sentiment-analysis",
                    model=self.model_name,
                    device=device,
                    max_length=512,
                    truncation=True
                )
                logger.info("Hugging Face model loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading Hugging Face pipeline: {e}. Falling back to lexicon analysis.")
                self.using_fallback = True
        else:
            self.using_fallback = True

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Runs sentiment analysis on a raw or cleaned text string.
        
        Args:
            text (str): Input text block.
            
        Returns:
            Dict[str, Any]: Sentiment dictionary containing:
                - sentiment_label (str): 'positive', 'neutral', 'negative'
                - sentiment_score (float): 1.0, 0.0, -1.0
                - sentiment_confidence (float): Probability score [0.0 - 1.0]
        """
        self.processed_count += 1
        
        if not text or not isinstance(text, str) or not text.strip():
            return {
                "sentiment_label": "neutral",
                "sentiment_score": 0.0,
                "sentiment_confidence": 1.0
            }

        # If using fallback or classifier didn't load
        if self.using_fallback or not self.classifier:
            self.fallback_count += 1
            res = self.fallback_analyzer.analyze(text)
            return {
                "sentiment_label": res["label"],
                "sentiment_score": res["score"],
                "sentiment_confidence": res["confidence"]
            }

        try:
            # Run RoBERTa model inference
            results = self.classifier(text)
            if not results:
                raise ValueError("Model returned empty results.")
                
            res = results[0]
            label_raw = res["label"].lower()
            confidence = res["score"]

            # Map RoBERTa labels (positive/neutral/negative or Label_X)
            # cardiffnlp latest maps: positive, neutral, negative
            if "positive" in label_raw or "label_2" in label_raw:
                label = "positive"
                score = 1.0
            elif "negative" in label_raw or "label_0" in label_raw:
                label = "negative"
                score = -1.0
            else:
                label = "neutral"
                score = 0.0

            return {
                "sentiment_label": label,
                "sentiment_score": score,
                "sentiment_confidence": round(confidence, 4)
            }
            
        except Exception as e:
            logger.debug(f"RoBERTa inference error: {e}. Applying lexicon fallback.")
            self.fallback_count += 1
            res = self.fallback_analyzer.analyze(text)
            return {
                "sentiment_label": res["label"],
                "sentiment_score": res["score"],
                "sentiment_confidence": res["confidence"]
            }

    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Returns performance diagnostics for auditing.
        """
        fallback_pct = (self.fallback_count / self.processed_count * 100) if self.processed_count > 0 else 0.0
        return {
            "model_name": "LexiconFallback" if self.using_fallback else f"RoBERTa ({self.model_name})",
            "records_processed": self.processed_count,
            "fallback_usage_pct": round(fallback_pct, 2)
        }
