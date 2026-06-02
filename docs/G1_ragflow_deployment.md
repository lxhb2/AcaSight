# G.1 RAGFlow Docker 部署方案

> 日期: 2026-05-30 | 作者: A方 | 状态: ✅方案就绪

## 1. 资源需求

| 资源 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 4核 | 8核 |
| 内存 | 16GB | 32GB |
| 磁盘 | 50GB SSD | 100GB SSD |
| Docker | 24+ | 29+ |
| Docker Compose | v2.0+ | v5.0+ |

## 2. 部署架构

```
┌──────────────────────────────────────────┐
│  AcaSight Backend (FastAPI :8000)        │
│    └── rag_service.py                    │
│         └── httpx → RAGFlow API :9380   │
├──────────────────────────────────────────┤
│  RAGFlow Docker Stack                    │
│  ┌────────────────────────────────┐      │
│  │ ragflow-server  (:9380)        │      │
│  │ ragflow-api     (:9380)        │      │
│  │ ragflow-worker  (background)   │      │
│  ├────────────────────────────────┤      │
│  │ Elasticsearch   (:9200)        │      │
│  │ MinIO           (:9001)        │      │
│  │ MySQL           (:3306)        │      │
│  │ Redis           (:6379)        │      │
│  └────────────────────────────────┘      │
└──────────────────────────────────────────┘
```

## 3. Docker Compose 配置

```yaml
# docker-compose.ragflow.yml
version: "3.8"

services:
  ragflow:
    image: infiniflow/ragflow:v0.25.5
    container_name: acasight-ragflow
    ports:
      - "9380:9380"
      - "80:80"
    volumes:
      - ragflow-data:/ragflow
    environment:
      - MYSQL_PASSWORD=acasight_ragflow_2026
      - MINIO_USER=acasight
      - MINIO_PASSWORD=acasight_minio_2026
      - REDIS_PASSWORD=acasight_redis_2026
    depends_on:
      - elasticsearch
      - mysql
      - minio
      - redis
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G

  elasticsearch:
    image: elasticsearch:8.11.0
    container_name: acasight-es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G

  mysql:
    image: mysql:8.0
    container_name: acasight-mysql
    environment:
      - MYSQL_ROOT_PASSWORD=acasight_ragflow_2026
      - MYSQL_DATABASE=ragflow
    volumes:
      - mysql-data:/var/lib/mysql
    ports:
      - "3306:3306"
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    container_name: acasight-minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=acasight
      - MINIO_ROOT_PASSWORD=acasight_minio_2026
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: acasight-redis
    command: redis-server --requirepass acasight_redis_2026
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  ragflow-data:
  es-data:
  mysql-data:
  minio-data:
  redis-data:
```

## 4. AcaSight 后端配置变更

### 4.1 .env 新增

```env
# RAGFlow Configuration
RAGFLOW_BASE_URL=http://localhost:9380
RAGFLOW_API_KEY=your-api-key-here
RAGFLOW_DATASET_IDS=
```

### 4.2 rag_service.py 已支持

当前 `rag_service.py` 已实现：
- `check_available()` — 检测 RAGFlow 连接
- `query()` — 查询 RAGFlow
- `list_datasets()` — 列出数据集
- 自动降级：RAGFlow 不可用时回退到普通 LLM

无需修改后端代码，只需配置环境变量。

## 5. 启动流程

```powershell
# 1. 启动 RAGFlow 栈
docker compose -f docker-compose.ragflow.yml up -d

# 2. 等待服务就绪（约 2-3 分钟）
docker compose -f docker-compose.ragflow.yml logs -f ragflow

# 3. 访问 RAGFlow Web UI
# http://localhost:80 → 注册账号 → 获取 API Key

# 4. 配置 AcaSight
# .env 中设置 RAGFLOW_API_KEY

# 5. 验证
curl http://localhost:8000/api/rag/status
```

## 6. 资源监控

```powershell
# 查看容器状态
docker compose -f docker-compose.ragflow.yml ps

# 查看资源使用
docker stats acasight-ragflow acasight-es acasight-mysql acasight-redis

# 查看日志
docker compose -f docker-compose.ragflow.yml logs -f --tail=50
```

## 7. 注意事项

1. **内存**: Elasticsearch + RAGFlow 至少需要 12GB 内存，建议 16GB+
2. **首次启动**: Elasticsearch 初始化需要 2-3 分钟
3. **API Key**: 需在 RAGFlow Web UI 注册后获取
4. **数据持久化**: 使用 Docker volumes，删除容器不丢失数据
5. **端口冲突**: 确保 9380/9200/3306/6379/9000/9001/80 端口可用
6. **备份**: 定期备份 mysql-data 和 es-data volumes
