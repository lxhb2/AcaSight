import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

RAGFLOW_BASE_URL = "http://localhost:9380"
RAGFLOW_API_KEY = ""


class RAGService:
    def __init__(self):
        self.base_url = RAGFLOW_BASE_URL
        self.api_key = RAGFLOW_API_KEY
        self.available = False

    async def check_available(self) -> bool:
        if not self.api_key:
            self.available = False
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/datasets",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                self.available = resp.status_code == 200
                return self.available
        except Exception as e:
            logger.warning(f"RAGFlow not available: {e}")
            self.available = False
            return False

    async def query(
        self,
        question: str,
        dataset_ids: Optional[list[str]] = None,
        chat_id: Optional[str] = None,
    ) -> dict:
        if not self.available:
            return {
                "answer": "RAGFlow 服务未连接。请确保 RAGFlow Docker 容器正在运行，并在 AI 配置中设置 RAGFlow API Key。",
                "source": "fallback",
                "available": False,
            }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload: dict = {
                    "question": question,
                }
                if dataset_ids:
                    payload["dataset_ids"] = dataset_ids
                if chat_id:
                    payload["chat_id"] = chat_id

                resp = await client.post(
                    f"{self.base_url}/api/v1/chats",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "answer": data.get("data", {}).get("answer", ""),
                        "reference": data.get("data", {}).get("reference", {}),
                        "chat_id": data.get("data", {}).get("chat_id"),
                        "source": "ragflow",
                        "available": True,
                    }
                else:
                    return {
                        "answer": f"RAGFlow 查询失败: {resp.status_code}",
                        "source": "error",
                        "available": True,
                    }
        except httpx.TimeoutException:
            return {
                "answer": "RAGFlow 查询超时，请稍后重试。",
                "source": "timeout",
                "available": True,
            }
        except Exception as e:
            return {
                "answer": f"RAGFlow 查询异常: {str(e)}",
                "source": "error",
                "available": True,
            }

    async def list_datasets(self) -> list[dict]:
        if not self.available:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/datasets",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if resp.status_code == 200:
                    return resp.json().get("data", [])
                return []
        except Exception:
            return []


_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
