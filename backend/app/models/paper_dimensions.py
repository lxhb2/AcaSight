"""
文献11维度结构化拆分模型

每篇文献固定拆分为11个维度，所有字段单独入库、结构化存储。
关联文献唯一ID，绑定知识图谱索引。
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class PaperDimensions(Base):
    __tablename__ = "paper_dimensions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    abstract = Column(Text, nullable=True)
    research_background = Column(Text, nullable=True)
    research_purpose = Column(Text, nullable=True)
    research_status = Column(Text, nullable=True)
    research_questions = Column(Text, nullable=True)
    basic_theory = Column(Text, nullable=True)
    research_methods = Column(Text, nullable=True)
    results_and_evaluation = Column(Text, nullable=True)
    innovation_points = Column(Text, nullable=True)
    limitations_and_suggestions = Column(Text, nullable=True)
    conclusions = Column(Text, nullable=True)

    graph_indexed = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    DIMENSION_KEYS = [
        "abstract", "research_background", "research_purpose", "research_status",
        "research_questions", "basic_theory", "research_methods",
        "results_and_evaluation", "innovation_points",
        "limitations_and_suggestions", "conclusions",
    ]

    DIMENSION_LABELS = {
        "abstract": "摘要",
        "research_background": "研究背景",
        "research_purpose": "研究目的与意义",
        "research_status": "研究现状",
        "research_questions": "研究问题",
        "basic_theory": "基本理论",
        "research_methods": "研究方法",
        "results_and_evaluation": "结果与评价",
        "innovation_points": "创新点",
        "limitations_and_suggestions": "局限与建议",
        "conclusions": "结论",
    }

    def to_dict(self, dimensions: list[str] | None = None) -> dict:
        keys = dimensions if dimensions else self.DIMENSION_KEYS
        result = {
            "id": self.id,
            "paper_id": self.paper_id,
        }
        for k in keys:
            result[k] = getattr(self, k, None)
        result["graph_indexed"] = self.graph_indexed
        result["created_at"] = self.created_at.isoformat() if self.created_at else None
        result["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return result
