"""
SAM3 Segmenter — 独立分割服务 (方向N.2)

支持:
- fal.ai SAM3 API
- Roboflow API
- 本地 SAM3 (可选)
- 多 text prompt 合并去重
- Box 合并 (overlap threshold)

设计:
- 独立于 figure_edit_service，可单独调用
- 复用全局 httpx 连接池
"""

import base64
import os
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
import structlog

from app.services.ai_service import get_http_client

logger = structlog.get_logger()

# ── 配置 ──

SAM3_BACKEND = os.getenv("SAM3_BACKEND", "fal")
SAM3_API_KEY = os.getenv("SAM3_API_KEY", "")
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_ENDPOINT = os.getenv("ROBOFLOW_ENDPOINT", "")


class SAM3Segmenter:
    """SAM3 图标/区域分割器"""

    def __init__(self, backend: Optional[str] = None):
        self.backend = backend or SAM3_BACKEND
        self.api_key = SAM3_API_KEY if self.backend in ("fal", "api") else ROBOFLOW_API_KEY

    @property
    def available(self) -> bool:
        if self.backend == "fal":
            return bool(SAM3_API_KEY)
        elif self.backend == "roboflow":
            return bool(ROBOFLOW_API_KEY and ROBOFLOW_ENDPOINT)
        elif self.backend == "local":
            # Check if local SAM3 model is available
            try:
                import segment_anything  # noqa: F401
                return True
            except ImportError:
                return False
        return False

    async def segment(
        self,
        image: Image.Image,
        prompts: str = "icon",
        min_score: float = 0.5,
        max_masks: int = 32,
        merge_threshold: float = 0.9,
    ) -> Dict[str, Any]:
        """
        执行 SAM3 分割。

        Args:
            image: PIL Image
            prompts: 逗号分隔的 text prompt
            min_score: 最低置信度
            max_masks: 最大 mask 数
            merge_threshold: Box 合并重叠阈值

        Returns:
            {"detections": [...], "image_size": [w, h], "total": N}
        """
        prompt_list = [p.strip() for p in prompts.split(",") if p.strip()]

        img_b64 = self._pil_to_b64(image)
        all_detections = []

        # 对每个 prompt 分别检测
        for prompt in prompt_list:
            dets = await self._detect(img_b64, [prompt], min_score, max_masks)
            for d in dets:
                d["prompt"] = prompt
            all_detections.extend(dets)

        # 去重: 合并重叠 boxes
        if merge_threshold > 0 and len(all_detections) > 1:
            all_detections = self._merge_overlapping_boxes(all_detections, merge_threshold)

        # 添加序号标签
        for i, det in enumerate(all_detections):
            det["label"] = f"<AF>{i+1:02d}"

        return {
            "detections": all_detections,
            "image_size": list(image.size),
            "total": len(all_detections),
        }

    async def _detect(
        self,
        image_b64: str,
        prompts: List[str],
        min_score: float,
        max_masks: int,
    ) -> List[Dict[str, Any]]:
        if self.backend == "fal":
            return await self._detect_fal(image_b64, prompts, min_score, max_masks)
        elif self.backend == "roboflow":
            return await self._detect_roboflow(image_b64, prompts, min_score)
        elif self.backend == "local":
            return await self._detect_local(image_b64, prompts, min_score)
        return []

    async def _detect_fal(
        self, image_b64: str, prompts: List[str], min_score: float, max_masks: int
    ) -> List[Dict[str, Any]]:
        if not SAM3_API_KEY:
            return []

        payload = {
            "image": f"data:image/png;base64,{image_b64}",
            "prompts": prompts,
            "min_score": min_score,
            "max_masks": max_masks,
        }

        try:
            client = await get_http_client()
            resp = await client.post(
                f"https://fal.run/fal-ai/sam3",
                headers={
                    "Authorization": f"Key {SAM3_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()

            detections = []
            for item in data.get("masks", []):
                bbox = item.get("bbox", [0, 0, 100, 100])
                detections.append({
                    "bbox": bbox,
                    "area": item.get("area", 0),
                    "score": item.get("score", 0.0),
                })
            return detections

        except Exception as e:
            logger.error("SAM3 FAL detection failed", error=str(e))
            return []

    async def _detect_roboflow(
        self, image_b64: str, prompts: List[str], min_score: float
    ) -> List[Dict[str, Any]]:
        if not ROBOFLOW_API_KEY or not ROBOFLOW_ENDPOINT:
            return []

        payload = {
            "image": image_b64,
            "prompts": prompts,
            "confidence": min_score,
        }

        try:
            client = await get_http_client()
            resp = await client.post(
                ROBOFLOW_ENDPOINT,
                headers={
                    "Authorization": ROBOFLOW_API_KEY,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("detections", [])

        except Exception as e:
            logger.error("SAM3 Roboflow detection failed", error=str(e))
            return []

    async def _detect_local(
        self, image_b64: str, prompts: List[str], min_score: float
    ) -> List[Dict[str, Any]]:
        """本地 SAM3 推理 (需要 segment-anything 安装)"""
        try:
            import numpy as np
            from segment_anything import SamPredictor, sam_model_registry

            # This is a simplified local inference stub
            # Full implementation would load the model and run inference
            logger.warning("Local SAM3 not fully implemented, returning empty")
            return []
        except ImportError:
            logger.error("segment-anything not installed")
            return []

    @staticmethod
    def _merge_overlapping_boxes(
        detections: List[Dict[str, Any]], threshold: float = 0.9
    ) -> List[Dict[str, Any]]:
        """合并重叠 boxes"""
        if not detections:
            return detections

        def overlap_ratio(box1_bbox, box2_bbox):
            x1 = max(box1_bbox[0], box2_bbox[0])
            y1 = max(box1_bbox[1], box2_bbox[1])
            x2 = min(box1_bbox[2], box2_bbox[2])
            y2 = min(box1_bbox[3], box2_bbox[3])

            if x2 <= x1 or y2 <= y1:
                return 0.0

            intersection = (x2 - x1) * (y2 - y1)
            area1 = (box1_bbox[2] - box1_bbox[0]) * (box1_bbox[3] - box1_bbox[1])
            area2 = (box2_bbox[2] - box2_bbox[0]) * (box2_bbox[3] - box2_bbox[1])
            smaller = min(area1, area2)

            return intersection / smaller if smaller > 0 else 0.0

        merged = list(detections)

        changed = True
        while changed:
            changed = False
            new_merged = []
            used = set()

            for i in range(len(merged)):
                if i in used:
                    continue
                current = merged[i]
                current_bbox = current.get("bbox", [0, 0, 100, 100])

                for j in range(i + 1, len(merged)):
                    if j in used:
                        continue
                    other = merged[j]
                    other_bbox = other.get("bbox", [0, 0, 100, 100])

                    if overlap_ratio(current_bbox, other_bbox) >= threshold:
                        # Merge: take the larger box
                        x1 = min(current_bbox[0], other_bbox[0])
                        y1 = min(current_bbox[1], other_bbox[1])
                        x2 = max(current_bbox[2], other_bbox[2])
                        y2 = max(current_bbox[3], other_bbox[3])
                        current["bbox"] = [x1, y1, x2, y2]
                        current["area"] = (x2 - x1) * (y2 - y1)
                        used.add(j)
                        changed = True

                new_merged.append(current)

            merged = new_merged

        return merged

    @staticmethod
    def _pil_to_b64(img: Image.Image) -> str:
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")


# Singleton
sam3_segmenter = SAM3Segmenter()
