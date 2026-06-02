"""
文献数据模型 — v6 Chapter C 重构

独立模型，不依赖 User 外键（单用户学术工具）。
标签采用 JSON 数组存储，简化架构。
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class Paper(Base):
    """文献模型"""
    __tablename__ = 'papers'

    id = Column(Integer, primary_key=True, index=True)
    paper_code = Column(String(30), unique=True, index=True, nullable=True)

    # ── 基本信息 ──
    title = Column(String(500), nullable=False, index=True)
    authors = Column(JSON, default=list)          # ["Author A", "Author B"]
    abstract = Column(Text)

    # ── 标识符 ──
    doi = Column(String(100), index=True)
    pmid = Column(String(20))
    arxiv_id = Column(String(50))
    openalex_id = Column(String(100))
    semanticscholar_id = Column(String(100))

    # ── 出版信息 ──
    journal = Column(String(200))
    year = Column(Integer, index=True)
    volume = Column(String(50))
    issue = Column(String(50))
    pages = Column(String(50))
    publisher = Column(String(200))

    # ── 文件信息 ──
    pdf_path = Column(String(500))
    file_size = Column(Integer)
    page_count = Column(Integer)

    # ── 元数据 ──
    keywords = Column(JSON, default=list)         # ["keyword1", "keyword2"]
    tags = Column(JSON, default=list)             # ["tag1", "tag2"] — 简化标签
    extra_fields = Column(JSON, default=dict)     # 扩展字段

    # ── 向量检索 ──
    vector_id = Column(String(100))

    # ── 统计 ──
    citation_count = Column(Integer, default=0)
    reference_count = Column(Integer, default=0)

    # ── 状态 ──
    is_favorite = Column(Integer, default=0)       # 0=否, 1=是
    read_status = Column(String(20), default='unread')  # unread / reading / read
    rating = Column(Integer, default=0)            # 1-5 星

    # ── 时间戳 ──
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Paper(id={self.id}, title='{self.title[:50]}...')>"

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'paper_code': self.paper_code,
            'title': self.title,
            'authors': self.authors or [],
            'abstract': self.abstract,
            'doi': self.doi,
            'pmid': self.pmid,
            'arxiv_id': self.arxiv_id,
            'openalex_id': self.openalex_id,
            'semanticscholar_id': self.semanticscholar_id,
            'journal': self.journal,
            'year': self.year,
            'volume': self.volume,
            'issue': self.issue,
            'pages': self.pages,
            'publisher': self.publisher,
            'pdf_path': self.pdf_path,
            'file_size': self.file_size,
            'page_count': self.page_count,
            'keywords': self.keywords or [],
            'tags': self.tags or [],
            'extra_fields': self.extra_fields or {},
            'citation_count': self.citation_count or 0,
            'reference_count': self.reference_count or 0,
            'is_favorite': self.is_favorite or 0,
            'read_status': self.read_status,
            'rating': self.rating or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
