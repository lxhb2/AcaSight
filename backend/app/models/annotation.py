"""
批注数据模型 — Chapter D

支持高亮、下划线、文本批注。
位置信息以 JSON 存储四角坐标，兼容 PDF 页面叠加渲染。
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from sqlalchemy.sql import func
from app.database import Base


class Annotation(Base):
    """PDF 批注模型"""
    __tablename__ = 'annotations'

    id = Column(Integer, primary_key=True, index=True)

    # ── 关联 ──
    paper_id = Column(Integer, index=True, nullable=True)   # 关联 papers 表（可选）
    pdf_hash = Column(String(64), index=True, nullable=False)  # PDF SHA256 哈希，唯一标识文件

    # ── 批注类型 ──
    # highlight: 高亮 | underline: 下划线 | note: 文本批注 | strikethrough: 删除线
    annotation_type = Column(String(20), nullable=False, default='highlight')

    # ── 位置信息 ──
    page = Column(Integer, nullable=False)                    # 页码（1-based）
    # rect: [x0, y0, x1, y1] 四角坐标（PDF 坐标系）
    rect = Column(JSON, nullable=False)

    # ── 内容 ──
    selected_text = Column(Text)                              # 被选中的原文
    note = Column(Text)                                       # 批注备注
    color = Column(String(20), default='#FFEB3B')             # 高亮颜色

    # ── 时间戳 ──
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Annotation(id={self.id}, type={self.annotation_type}, page={self.page})>"

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'paper_id': self.paper_id,
            'pdf_hash': self.pdf_hash,
            'annotation_type': self.annotation_type,
            'page': self.page,
            'rect': self.rect or [],
            'selected_text': self.selected_text,
            'note': self.note,
            'color': self.color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
