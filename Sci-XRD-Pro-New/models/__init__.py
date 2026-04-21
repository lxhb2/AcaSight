"""
Sci-XRD Pro - 数据模型
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np


@dataclass
class PeakModel:
    """峰位数据模型"""
    position: float
    intensity: float
    d_spacing: float
    fwhm: float = 0.1
    prominence: float = 0.0
    label: str = ""
    method: str = ""
    confidence: float = 1.0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PhaseModel:
    """物相数据模型"""
    name: str
    formula: str
    score: float
    n_matched: int = 0
    pdf_number: str = ""
    system: str = ""
    d_fom: float = 0.0
    i_fom: float = 0.0
    m_fom: float = 0.0
    method: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class XRDDataModel:
    """XRD数据模型"""
    angles: np.ndarray
    intensities: np.ndarray
    filename: str = ""
    format: str = ""
    peaks: List[PeakModel] = field(default_factory=list)
    phases: List[PhaseModel] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    wavelength: float = 1.5406
    ai_results: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    is_analyzed: bool = False
    analysis_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'filename': self.filename,
            'format': self.format,
            'wavelength': self.wavelength,
            'metadata': self.metadata,
            'peaks': [p.to_dict() for p in self.peaks],
            'phases': [ph.to_dict() for ph in self.phases],
            'ai_results': self.ai_results,
            'timestamp': self.timestamp.isoformat(),
            'is_analyzed': self.is_analyzed,
            'analysis_params': self.analysis_params
        }
    
    def save(self, filepath: str):
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


@dataclass
class AIAnalysisResult:
    """AI分析结果"""
    response: str
    analysis_type: str
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
