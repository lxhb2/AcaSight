"""
文档管理数据模型 — Phase 2 OnlyOffice 集成

Document: 文档主表，存储文档元数据
DocumentVersion: 文档版本表，记录每次保存的历史版本
"""

import uuid
from sqlalchemy import Column, String, Integer, BigInteger, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Document(Base):
    """文档模型"""
    __tablename__ = 'documents'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_type = Column(String(10), nullable=False, index=True)  # docx / xlsx / pptx
    size_bytes = Column(BigInteger, default=0)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    metadata_json = Column(JSON, default=dict)

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title[:50]}...', type={self.file_type})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'size_bytes': self.size_bytes,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata_json': self.metadata_json or {},
        }


class DocumentVersion(Base):
    """文档版本模型"""
    __tablename__ = 'document_versions'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    file_path = Column(String(1000), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    change_summary = Column(Text, nullable=True)

    def __repr__(self):
        return f"<DocumentVersion(id={self.id}, doc_id={self.document_id}, v{self.version_number})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'version_number': self.version_number,
            'file_path': self.file_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'change_summary': self.change_summary,
        }
