"""
绘图模块Agent — 自动绘图、AI推荐、模板生成、数据解析、保存

复用现有 chart_auto + chartTemplates + unified_storage_service
"""

from app.agent.base_module import BaseModule, ModuleResult, ModuleStatus
from app.services.ai_service import ai_service
import structlog
import json

logger = structlog.get_logger()


class ChartAgent(BaseModule):
    def __init__(self):
        super().__init__(name="chart", description="绘图模块Agent: 自动绘图/AI推荐/模板/数据解析/保存")

    async def execute(self, task: str, context: dict = None) -> ModuleResult:
        self._status = ModuleStatus.RUNNING
        ctx = context or {}

        try:
            task_lower = task.lower()
            if "绘图" in task or "chart" in task_lower or "图" in task:
                result = await self._handle_chart(task, ctx)
            elif "推荐" in task or "recommend" in task_lower:
                result = await self._handle_recommend(task, ctx)
            elif "保存" in task or "save" in task_lower:
                result = await self._handle_save(task, ctx)
            elif "模板" in task or "template" in task_lower:
                result = await self._handle_template(task, ctx)
            elif "数据" in task or "data" in task_lower or "解析" in task:
                result = await self._handle_data_parse(task, ctx)
            else:
                result = await self._handle_general(task, ctx)

            self._status = ModuleStatus.COMPLETED
            self._last_result = result
            self._record_history(task, result)
            return result

        except Exception as e:
            self._status = ModuleStatus.FAILED
            result = ModuleResult(success=False, error=str(e))
            self._last_result = result
            self._record_history(task, result)
            logger.error("ChartAgent failed", error=str(e))
            return result

    async def _handle_chart(self, task: str, ctx: dict) -> ModuleResult:
        description = ctx.get("description", task)
        columns = ctx.get("columns", [])
        sample_data = ctx.get("sample_data", [])
        chart_type = ctx.get("chart_type", "auto")

        try:
            from app.services.ai_service import ai_service
            parts = []
            if description.strip():
                parts.append(f"用户需求: {description.strip()}")
            if columns:
                cols_desc = ", ".join([f"{c.get('name','?')}({c.get('type','?')})" for c in columns])
                parts.append(f"列定义: {cols_desc}")
            if sample_data:
                parts.append(f"样本数据(前3行): {json.dumps(sample_data[:3], ensure_ascii=False)}")

            prompt_text = "\n".join(parts)
            messages = [
                {"role": "system", "content": "你是科研绘图配置专家。根据用户需求和数据，推荐最合适的图表类型和配置。返回JSON格式：{chart_type, title, x_axis, y_axis, color_by, config}"},
                {"role": "user", "content": prompt_text},
            ]
            response = ""
            async for chunk in ai_service.chat(messages, temperature=0.3):
                response += chunk

            try:
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0]
                config = json.loads(json_str.strip())
                return ModuleResult(success=True, data={"type": "chart_config", "config": config})
            except Exception:
                return ModuleResult(success=True, data={"type": "chart_config", "raw": response})

        except Exception as e:
            return ModuleResult(success=False, error=f"绘图配置生成失败: {e}")

    async def _handle_recommend(self, task: str, ctx: dict) -> ModuleResult:
        data_description = ctx.get("data_description", task)
        messages = [
            {"role": "system", "content": "你是科研绘图专家，根据数据特征推荐最合适的图表类型。返回推荐列表，每项包含：chart_type, reason, when_to_use。"},
            {"role": "user", "content": f"数据描述：{data_description}\n请推荐3种最适合的图表类型和理由。"},
        ]
        response = await ai_service.chat(messages)
        return ModuleResult(success=True, data={"type": "recommendation", "content": response})

    async def _handle_save(self, task: str, ctx: dict) -> ModuleResult:
        image_data = ctx.get("image_data")
        filename = ctx.get("filename", "chart.png")
        raw_data = ctx.get("raw_data")
        edit_params = ctx.get("edit_params")
        paper_id = ctx.get("paper_id")

        if not image_data:
            return ModuleResult(success=False, error="需要 image_data")

        try:
            from app.services.unified_storage_service import get_unified_storage
            ai_service = get_unified_storage()
            result = ai_service.save_chart_product(
                image_data=image_data,
                filename=filename,
                raw_data=raw_data,
                edit_params=edit_params,
                paper_id=paper_id,
            )
            return ModuleResult(success=True, data={"type": "save", "path": result.get("path", ""), "filename": filename})
        except Exception as e:
            return ModuleResult(success=False, error=f"保存失败: {e}")

    async def _handle_template(self, task: str, ctx: dict) -> ModuleResult:
        try:
            from app.components.Charts.chartTemplates import CHART_TEMPLATES
            templates = [{"id": t.get("id", i), "name": t.get("name", f"Template {i}"), "type": t.get("type", "")}
                         for i, t in enumerate(CHART_TEMPLATES)]
            return ModuleResult(success=True, data={"type": "templates", "templates": templates, "count": len(templates)})
        except Exception:
            return ModuleResult(success=True, data={"type": "templates", "templates": [], "message": "模板库请通过 /api/chart/auto 端点获取"})

    async def _handle_data_parse(self, task: str, ctx: dict) -> ModuleResult:
        raw_data = ctx.get("raw_data", "")
        if not raw_data:
            return ModuleResult(success=False, error="需要 raw_data")

        messages = [
            {"role": "system", "content": "你是数据解析专家。分析原始数据，提取列定义、数据类型和统计摘要。返回JSON格式：{columns: [{name, type, sample}], row_count, statistics: {numeric_cols: {min, max, mean}, categorical_cols: {unique_count}}}"},
            {"role": "user", "content": f"请解析以下数据：\n{raw_data[:3000]}"},
        ]
        response = await ai_service.chat(messages, temperature=0.3)
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            parsed = json.loads(json_str.strip())
            return ModuleResult(success=True, data={"type": "data_parse", "parsed": parsed})
        except Exception:
            return ModuleResult(success=True, data={"type": "data_parse", "raw": response})

    async def _handle_general(self, task: str, ctx: dict) -> ModuleResult:
        messages = [
            {"role": "system", "content": "你是科研绘图助手，擅长数据可视化和学术图表设计。"},
            {"role": "user", "content": task},
        ]
        response = await ai_service.chat(messages)
        return ModuleResult(success=True, data={"type": "general", "response": response})
