from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class SentimentSummary:
    brand: str
    total_records: Optional[int]
    positive_pct: Optional[float]
    neutral_pct: Optional[float]
    negative_pct: Optional[float]
    net_sentiment: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TopicGap:
    topic: str
    mamaearth: int
    minimalist: int
    gap: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Recommendation:
    topic: str
    observation: str
    evidence: str
    recommendation: str
    confidence: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DashboardData:
    title: str
    metrics: Dict[str, Any]
    tables: Dict[str, List[Dict[str, Any]]]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
