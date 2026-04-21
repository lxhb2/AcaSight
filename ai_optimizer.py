#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI辅助功能优化模块
"""

import json
import time
import threading
import queue
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import sqlite3

@dataclass
class AIRequest:
    """AI请求封装"""
    request_id: str
    prompt: str
    context: Dict[str, Any]
    callback: Callable
    error_callback: Optional[Callable] = None
    timeout: int = 30  # 默认30秒超时
    retry_count: int = 3  # 重试次数

class AIOptimizer:
    """AI功能优化器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or r"F:\桌面\pdf2_final_complete.db"
        self.request_queue = queue.Queue()
        self.results_cache = {}  # 请求结果缓存
        self.is_running = True
        self.worker_thread = None
        
        # 初始化Ollama
        self._init_ollama()
        
        # 启动工作线程
        self._start_worker()
    
    def _init_ollama(self):
        """初始化Ollama客户端"""
        try:
            import ollama
            self.ollama = ollama
            self.ollama_available = True
            print("Ollama客户端初始化成功")
        except ImportError:
            self.ollama = None
            self.ollama_available = False
            print("警告: Ollama未安装，AI功能将受限")
    
    def _start_worker(self):
        """启动工作线程"""
        self.worker_thread = threading.Thread(target=self._process_requests, daemon=True)
        self.worker_thread.start()
        print("AI工作线程已启动")
    
    def _process_requests(self):
        """处理AI请求队列"""
        while self.is_running:
            try:
                # 从队列获取请求（非阻塞）
                try:
                    request = self.request_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # 处理请求
                self._handle_request(request)
                
                # 标记任务完成
                self.request_queue.task_done()
                
            except Exception as e:
                print(f"AI请求处理错误: {e}")
                time.sleep(1)
    
    def _handle_request(self, request: AIRequest):
        """处理单个AI请求"""
        start_time = time.time()
        
        # 检查缓存
        cache_key = self._generate_cache_key(request)
        if cache_key in self.results_cache:
            print(f"使用缓存结果: {request.request_id}")
            request.callback(self.results_cache[cache_key])
            return
        
        # 执行AI请求
        result = None
        last_error = None
        
        for attempt in range(request.retry_count):
            try:
                if not self.ollama_available:
                    result = self._fallback_response(request)
                    break
                
                # 构建提示词
                prompt = self._build_prompt(request)
                
                # 调用Ollama
                response = self.ollama.generate(
                    model="qwen3.5:0.8b",
                    prompt=prompt,
                    options={
                        "temperature": 0.3,
                        "num_predict": 1000,
                        "top_p": 0.9
                    }
                )
                
                # 解析响应
                result = self._parse_response(response, request)
                
                # 缓存结果
                self.results_cache[cache_key] = result
                
                # 成功，跳出重试循环
                break
                
            except Exception as e:
                last_error = e
                print(f"AI请求失败 (尝试 {attempt + 1}/{request.retry_count}): {e}")
                
                if attempt < request.retry_count - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    # 所有重试都失败，使用降级方案
                    result = self._fallback_response(request, error=str(e))
        
        # 计算耗时
        elapsed = time.time() - start_time
        
        # 调用回调
        if result:
            result['processing_time'] = elapsed
            request.callback(result)
        elif request.error_callback:
            request.error_callback(f"AI请求失败: {last_error}")
    
    def _generate_cache_key(self, request: AIRequest) -> str:
        """生成缓存键"""
        import hashlib
        content = f"{request.prompt}:{json.dumps(request.context, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _build_prompt(self, request: AIRequest) -> str:
        """构建提示词"""
        prompt_templates = {
            "recommend_params": """
你是一个XRD分析专家。请根据以下数据特征推荐分析参数：

数据特征：
{context}

请以JSON格式返回推荐参数，包含以下字段：
- smooth_window: 平滑窗口大小 (整数)
- background_lambda: 背景扣除lambda值 (浮点数)
- peak_height_threshold: 峰高阈值百分比 (浮点数)
- peak_prominence: 峰突出度阈值 (浮点数)
- min_peak_distance: 最小峰间距 (浮点数)
- 推荐理由: 简要说明推荐理由

示例响应：
{{
  "smooth_window": 7,
  "background_lambda": 1000.0,
  "peak_height_threshold": 1.5,
  "peak_prominence": 1.0,
  "min_peak_distance": 0.3,
  "推荐理由": "数据噪声较大，建议使用较大的平滑窗口和较高的背景扣除参数"
}}
""",
            "analyze_phases": """
你是一个XRD物相分析专家。请分析以下匹配结果：

匹配结果：
{context}

请分析：
1. 最可能的物相是什么？
2. 匹配的置信度如何？
3. 有哪些异常或需要注意的地方？
4. 建议的下一步分析方向？

请以JSON格式返回分析结果。
""",
            "explain_results": """
你是一个XRD结果解释专家。请解释以下分析结果：

分析结果：
{context}

请用通俗易懂的语言解释：
1. 这个XRD谱图显示了什么？
2. 鉴定出的物相有什么意义？
3. 峰形和峰宽说明了什么？
4. 给用户的建议是什么？

请以JSON格式返回解释结果。
"""
        }
        
        template = prompt_templates.get(request.prompt, request.prompt)
        return template.format(context=json.dumps(request.context, ensure_ascii=False, indent=2))
    
    def _parse_response(self, response, request: AIRequest) -> Dict[str, Any]:
        """解析AI响应"""
        try:
            # 尝试解析JSON
            content = response.get('response', '{}')
            
            # 提取可能的JSON部分
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # 如果不是JSON，返回原始文本
                return {"response": content.strip()}
                
        except json.JSONDecodeError:
            # JSON解析失败，返回原始响应
            return {"response": response.get('response', '').strip()}
    
    def _fallback_response(self, request: AIRequest, error: str = None) -> Dict[str, Any]:
        """降级响应（当AI不可用时）"""
        fallback_responses = {
            "recommend_params": {
                "smooth_window": 5,
                "background_lambda": 1000.0,
                "peak_height_threshold": 2.0,
                "peak_prominence": 1.0,
                "min_peak_distance": 0.3,
                "推荐理由": "使用默认参数（AI服务不可用）",
                "fallback": True,
                "error": error
            },
            "analyze_phases": {
                "分析": "AI服务暂时不可用，请检查匹配结果中的FOM分数和匹配率",
                "建议": "手动检查匹配结果，或稍后重试AI分析",
                "fallback": True,
                "error": error
            },
            "explain_results": {
                "解释": "AI解释服务暂时不可用",
                "建议": "请直接查看分析结果表格和图表",
                "fallback": True,
                "error": error
            }
        }
        
        response = fallback_responses.get(request.prompt, {
            "response": f"AI服务暂时不可用: {error}",
            "fallback": True
        })
        
        return response
    
    def submit_request(self, request_id: str, prompt_type: str, 
                      context: Dict[str, Any], 
                      callback: Callable,
                      error_callback: Optional[Callable] = None) -> str:
        """提交AI请求"""
        request = AIRequest(
            request_id=request_id,
            prompt=prompt_type,
            context=context,
            callback=callback,
            error_callback=error_callback
        )
        
        self.request_queue.put(request)
        print(f"AI请求已提交: {request_id} ({prompt_type})")
        return request_id
    
    def get_cached_result(self, prompt: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        cache_key = self._generate_cache_key(
            AIRequest(request_id="", prompt=prompt, context=context, callback=lambda x: None)
        )
        return self.results_cache.get(cache_key)
    
    def clear_cache(self):
        """清空缓存"""
        self.results_cache.clear()
        print("AI缓存已清空")
    
    def stop(self):
        """停止AI优化器"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        print("AI优化器已停止")

# 使用示例
if __name__ == "__main__":
    import re
    
    # 创建优化器
    optimizer = AIOptimizer()
    
    # 示例回调函数
    def on_result(result):
        print(f"收到AI结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    def on_error(error):
        print(f"AI请求错误: {error}")
    
    # 提交示例请求
    context = {
        "n_points": 2000,
        "angle_range": "5-80",
        "max_intensity": 5000,
        "estimated_peaks": 15,
        "noise_level": "高",
        "bg_drift": "严重"
    }
    
    optimizer.submit_request(
        request_id="test_001",
        prompt_type="recommend_params",
        context=context,
        callback=on_result,
        error_callback=on_error
    )
    
    # 等待处理
    time.sleep(5)
    
    # 停止优化器
    optimizer.stop()