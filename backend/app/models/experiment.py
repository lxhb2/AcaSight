"""
实验笔记本数据模型 — Feature 6.6

Experiment: 实验主表
ExperimentEntry: 实验条目（文本/数据/表格/图片/步骤）
ExperimentLink: 实验关联链接（文献/文档/图表）
"""

import uuid
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from app.database import Base


class Experiment(Base):
    """实验模型"""
    __tablename__ = 'experiments'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, default='')
    category = Column(String(100), default='')  # 实验分类标签
    status = Column(String(20), default='planning', index=True)  # planning / running / completed / failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    metadata_json = Column(JSON, default=dict)  # 扩展元数据

    def __repr__(self):
        return f"<Experiment(id={self.id[:8]}, title='{self.title[:30]}', status={self.status})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description or '',
            'category': self.category or '',
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata_json': self.metadata_json or {},
        }


class ExperimentEntry(Base):
    """实验条目模型"""
    __tablename__ = 'experiment_entries'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False, index=True)
    entry_type = Column(String(20), nullable=False)  # text / data / table / image / procedure
    content = Column(JSON, default=dict)  # 条目内容（JSON 结构）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tags = Column(JSON, default=list)  # 标签数组

    def __repr__(self):
        return f"<ExperimentEntry(id={self.id[:8]}, type={self.entry_type})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'entry_type': self.entry_type,
            'content': self.content or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'tags': self.tags or [],
        }


class ExperimentLink(Base):
    """实验关联链接模型"""
    __tablename__ = 'experiment_links'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False, index=True)
    linked_type = Column(String(20), nullable=False)  # literature / document / chart
    linked_id = Column(String(200), nullable=False)  # 关联对象的 ID
    note = Column(Text, default='')  # 关联备注
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ExperimentLink(id={self.id[:8]}, type={self.linked_type}, linked={self.linked_id})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'linked_type': self.linked_type,
            'linked_id': self.linked_id,
            'note': self.note or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
