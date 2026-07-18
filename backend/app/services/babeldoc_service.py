"""
BabelDOC 翻译服务 — PDF 全文翻译与双语对照

功能:
- 调用 BabelDOC 进行 PDF 全文翻译
- 生成单语翻译 PDF 和双语对照 PDF
- 支持交替页双语模式
- 异步进度报告
- 自动使用 AcaSight 的 AI 配置（OpenAI 兼容 API）
- 翻译结果缓存与状态管理
"""

import asyncio
import hashlib
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# 翻译输出目录
TRANSLATE_OUTPUT_DIR = Path(os.environ.get("ACASIGHT_TRANSLATE_DIR", "data/translations"))
TRANSLATE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def is_available() -> bool:
    """检查 BabelDOC 是否可用"""
    try:
        from babeldoc.format.pdf.high_level import translate
        from babeldoc.format.pdf.translation_config import TranslationConfig
        return True
    except ImportError:
        return False


class BabelDOCStatus:
    """翻译任务状态"""
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status: str = "pending"  # pending | running | completed | failed | cancelled
        self.progress: float = 0.0
        self.stage: str = ""
        self.created_at: float = time.time()
        self.completed_at: Optional[float] = None
        self.error: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": round(self.progress, 1),
            "stage": self.stage,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "result": self.result,
        }


class BabelDOCService:
    """BabelDOC PDF 翻译服务"""

    def __init__(self):
        self._tasks: Dict[str, BabelDOCStatus] = {}
        self._available = is_available()
        if self._available:
            logger.info("BabelDOC service initialized successfully")
        else:
            logger.warning("BabelDOC not available - install with: pip install babeldoc")

    @property
    def available(self) -> bool:
        return self._available

    @property
    def status(self) -> Dict:
        return {
            "available": self._available,
            "active_tasks": len([t for t in self._tasks.values() if t.status == "running"]),
            "total_tasks": len(self._tasks),
        }

    def get_task(self, task_id: str) -> Optional[BabelDOCStatus]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list:
        return [t.to_dict() for t in self._tasks.values()]

    def _make_task_id(self, pdf_path: str, lang_out: str) -> str:
        key = f"{pdf_path}:{lang_out}:{time.time()}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def _get_output_dir(self, task_id: str) -> Path:
        d = TRANSLATE_OUTPUT_DIR / task_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def start_translation(
        self,
        pdf_path: str,
        lang_in: str = "en",
        lang_out: str = "zh",
        no_dual: bool = False,
        no_mono: bool = True,
        use_alternating_pages_dual: bool = False,
        dual_translate_first: bool = False,
        pages: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-4o-mini",
        custom_system_prompt: Optional[str] = None,
    ) -> str:
        """启动 PDF 翻译任务，返回 task_id"""
        if not self._available:
            raise RuntimeError("BabelDOC is not installed")

        # 验证 PDF 文件存在
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        task_id = self._make_task_id(pdf_path, lang_out)
        status = BabelDOCStatus(task_id)
        status.status = "pending"
        self._tasks[task_id] = status

        output_dir = self._get_output_dir(task_id)

        # 在后台线程中执行翻译
        asyncio.create_task(self._run_translation(
            task_id=task_id,
            pdf_path=pdf_path,
            lang_in=lang_in,
            lang_out=lang_out,
            output_dir=output_dir,
            no_dual=no_dual,
            no_mono=no_mono,
            use_alternating_pages_dual=use_alternating_pages_dual,
            dual_translate_first=dual_translate_first,
            pages=pages,
            openai_base_url=openai_base_url,
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            custom_system_prompt=custom_system_prompt,
        ))

        return task_id

    async def _run_translation(
        self,
        task_id: str,
        pdf_path: str,
        lang_in: str,
        lang_out: str,
        output_dir: Path,
        no_dual: bool,
        no_mono: bool,
        use_alternating_pages_dual: bool,
        dual_translate_first: bool,
        pages: Optional[str],
        openai_base_url: Optional[str],
        openai_api_key: Optional[str],
        openai_model: str,
        custom_system_prompt: Optional[str],
    ):
        """在后台线程中执行翻译"""
        status = self._tasks[task_id]
        status.status = "running"
        status.stage = "初始化"

        try:
            result = await asyncio.to_thread(
                self._translate_sync,
                pdf_path=pdf_path,
                lang_in=lang_in,
                lang_out=lang_out,
                output_dir=output_dir,
                no_dual=no_dual,
                no_mono=no_mono,
                use_alternating_pages_dual=use_alternating_pages_dual,
                dual_translate_first=dual_translate_first,
                pages=pages,
                openai_base_url=openai_base_url,
                openai_api_key=openai_api_key,
                openai_model=openai_model,
                custom_system_prompt=custom_system_prompt,
                status=status,
            )

            status.status = "completed"
            status.progress = 100.0
            status.completed_at = time.time()
            status.result = result
            logger.info(f"Translation task {task_id} completed")

        except Exception as e:
            status.status = "failed"
            status.error = str(e)
            status.completed_at = time.time()
            logger.error(f"Translation task {task_id} failed: {e}")

    def _translate_sync(
        self,
        pdf_path: str,
        lang_in: str,
        lang_out: str,
        output_dir: Path,
        no_dual: bool,
        no_mono: bool,
        use_alternating_pages_dual: bool,
        dual_translate_first: bool,
        pages: Optional[str],
        openai_base_url: Optional[str],
        openai_api_key: Optional[str],
        openai_model: str,
        custom_system_prompt: Optional[str],
        status: BabelDOCStatus,
    ) -> Dict[str, Any]:
        """同步执行翻译（在线程池中运行）"""
        from babeldoc.format.pdf.high_level import translate, init
        from babeldoc.format.pdf.translation_config import TranslationConfig, WatermarkOutputMode
        from babeldoc.translator.translator import OpenAITranslator

        # 初始化 BabelDOC 资源
        init()

        # 创建翻译器
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "sk-placeholder")
        base_url = openai_base_url or os.environ.get("OPENAI_BASE_URL", None)

        translator = OpenAITranslator(
            lang_in=lang_in,
            lang_out=lang_out,
            model=openai_model,
            api_key=api_key,
            base_url=base_url,
        )

        # 构建翻译配置
        config = TranslationConfig(
            translator=translator,
            input_file=pdf_path,
            lang_in=lang_in,
            lang_out=lang_out,
            doc_layout_model=None,  # 自动加载
            output_dir=str(output_dir),
            no_dual=no_dual,
            no_mono=no_mono,
            use_alternating_pages_dual=use_alternating_pages_dual,
            dual_translate_first=dual_translate_first,
            watermark_output_mode=WatermarkOutputMode.NoWatermark,
            pages=pages,
            custom_system_prompt=custom_system_prompt,
            auto_extract_glossary=True,
            skip_clean=True,
        )

        # 执行翻译
        status.stage = "翻译中"
        result = translate(config)

        # 收集结果
        output = {
            "original_pdf": pdf_path,
            "lang_in": lang_in,
            "lang_out": lang_out,
            "mono_pdf": None,
            "dual_pdf": None,
        }

        if result.mono_pdf_path and result.mono_pdf_path.exists():
            # 复制到输出目录并使用标准命名
            mono_name = f"{Path(pdf_path).stem}-translated.pdf"
            mono_dest = output_dir / mono_name
            if str(result.mono_pdf_path) != str(mono_dest):
                shutil.copy2(result.mono_pdf_path, mono_dest)
            output["mono_pdf"] = str(mono_dest)

        if result.dual_pdf_path and result.dual_pdf_path.exists():
            dual_name = f"{Path(pdf_path).stem}-bilingual.pdf"
            dual_dest = output_dir / dual_name
            if str(result.dual_pdf_path) != str(dual_dest):
                shutil.copy2(result.dual_pdf_path, dual_dest)
            output["dual_pdf"] = str(dual_dest)

        if hasattr(result, "total_seconds") and result.total_seconds:
            output["total_seconds"] = round(result.total_seconds, 1)

        if hasattr(result, "total_valid_character_count") and result.total_valid_character_count:
            output["total_valid_chars"] = result.total_valid_character_count

        return output

    def cancel_translation(self, task_id: str) -> bool:
        """取消翻译任务"""
        status = self._tasks.get(task_id)
        if not status or status.status != "running":
            return False
        status.status = "cancelled"
        status.completed_at = time.time()
        return True

    def get_translated_pdf_path(self, task_id: str, pdf_type: str = "dual") -> Optional[str]:
        """获取翻译后的 PDF 路径"""
        status = self._tasks.get(task_id)
        if not status or status.status != "completed" or not status.result:
            return None
        key = f"{pdf_type}_pdf"
        return status.result.get(key)

    def cleanup_task(self, task_id: str):
        """清理任务输出文件"""
        status = self._tasks.get(task_id)
        if not status:
            return
        output_dir = TRANSLATE_OUTPUT_DIR / task_id
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
        del self._tasks[task_id]


# 全局单例
babeldoc_service = BabelDOCService()
