"""
优化版Ollama客户端 - 专为XRD分析设计
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import numpy as np
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import hashlib
import pickle
import os


@dataclass
class AIAnalysisResult:
    """AI分析结果"""
    peaks: List[Dict]
    phases: List[Dict]
    confidence: float
    suggestions: List[str]
    processing_time: float
    model_used: str


class OptimizedOllamaClient:
    """优化版Ollama客户端"""
    
    def __init__(self, 
                 model: str = "qwen3.5:0.8b",
                 base_url: str = "http://localhost:11434",
                 cache_dir: str = "ai_cache"):
        """
        初始化优化客户端
        
        Args:
            model: 使用的模型名称
            base_url: Ollama服务地址
            cache_dir: 缓存目录
        """
        self.model = model
        self.base_url = base_url
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 性能优化
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.cache = {}
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'avg_response_time': 0,
            'total_processing_time': 0
        }
        
        # XRD专用提示模板
        self.prompt_templates = {
            'peak_analysis': self._peak_analysis_prompt(),
            'phase_matching': self._phase_matching_prompt(),
            'quality_assessment': self._quality_assessment_prompt(),
            'optimization_suggestions': self._optimization_suggestions_prompt()
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
        self.executor.shutdown(wait=True)
    
    def _get_cache_key(self, data: Dict, prompt_type: str) -> str:
        """生成缓存键"""
        # 使用数据的哈希值作为缓存键
        data_str = json.dumps(data, sort_keys=True)
        prompt_str = prompt_type
        combined = f"{data_str}_{prompt_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存加载"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        return None
    
    def _save_to_cache(self, cache_key: str, data: Any):
        """保存到缓存"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except:
            pass
    
    async def analyze_xrd_data(self, 
                              angles: np.ndarray,
                              intensities: np.ndarray,
                              analysis_type: str = 'full') -> AIAnalysisResult:
        """
        AI分析XRD数据（优化版）
        
        Args:
            angles: 角度数组
            intensities: 强度数组
            analysis_type: 分析类型 ('full', 'peaks', 'phases', 'quality')
            
        Returns:
            AI分析结果
        """
        start_time = time.time()
        
        # 准备数据
        data_summary = self._summarize_data(angles, intensities)
        cache_key = self._get_cache_key(data_summary, analysis_type)
        
        # 检查缓存
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            self.stats['cache_hits'] += 1
            cached_result.processing_time = time.time() - start_time
            return cached_result
        
        # 构建提示
        prompt = self._build_analysis_prompt(data_summary, analysis_type)
        
        try:
            # 异步查询模型
            response_text = await self._query_model_optimized(prompt)
            
            # 解析响应
            result = self._parse_ai_response(response_text, analysis_type)
            result.processing_time = time.time() - start_time
            result.model_used = self.model
            
            # 更新统计
            self.stats['total_requests'] += 1
            self.stats['total_processing_time'] += result.processing_time
            self.stats['avg_response_time'] = (
                self.stats['total_processing_time'] / self.stats['total_requests']
            )
            
            # 缓存结果
            self._save_to_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            # 返回降级结果
            return self._get_fallback_result(angles, intensities, str(e))
    
    async def _query_model_optimized(self, prompt: str) -> str:
        """优化版模型查询"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # 优化请求参数
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # 降低随机性，提高一致性
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 512,  # 限制输出长度
                "seed": 42  # 固定种子，提高可重复性
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)  # 10秒超时
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('response', '')
                else:
                    raise Exception(f"API请求失败: {response.status}")
                    
        except asyncio.TimeoutError:
            raise Exception("请求超时")
        except Exception as e:
            raise Exception(f"模型查询失败: {e}")
    
    def _summarize_data(self, angles: np.ndarray, intensities: np.ndarray) -> Dict:
        """数据摘要（减少传输数据量）"""
        # 采样数据点（最多100个）
        n_points = len(angles)
        if n_points > 100:
            indices = np.linspace(0, n_points-1, 100, dtype=int)
            angles_sample = angles[indices]
            intensities_sample = intensities[indices]
        else:
            angles_sample = angles
            intensities_sample = intensities
        
        # 计算统计信息
        return {
            'n_points': n_points,
            'angle_range': [float(angles.min()), float(angles.max())],
            'intensity_range': [float(intensities.min()), float(intensities.max())],
            'sampled_angles': angles_sample.tolist(),
            'sampled_intensities': intensities_sample.tolist(),
            'mean_intensity': float(intensities.mean()),
            'std_intensity': float(intensities.std()),
            'max_intensity_position': float(angles[np.argmax(intensities)])
        }
    
    def _build_analysis_prompt(self, data_summary: Dict, analysis_type: str) -> str:
        """构建分析提示"""
        template = self.prompt_templates.get(analysis_type, self.prompt_templates['peak_analysis'])
        
        prompt = f"""你是一个专业的XRD分析专家。请分析以下XRD数据：

数据信息：
- 数据点数：{data_summary['n_points']}
- 角度范围：{data_summary['angle_range'][0]:.2f}° - {data_summary['angle_range'][1]:.2f}°
- 强度范围：{data_summary['intensity_range'][0]:.2f} - {data_summary['intensity_range'][1]:.2f}
- 平均强度：{data_summary['mean_intensity']:.2f}
- 最大强度位置：{data_summary['max_intensity_position']:.2f}°

采样数据（角度, 强度）：
"""
        
        # 添加采样数据
        for angle, intensity in zip(data_summary['sampled_angles'], 
                                   data_summary['sampled_intensities']):
            prompt += f"{angle:.2f}°, {intensity:.2f}\n"
        
        prompt += f"\n{template}"
        
        return prompt
    
    def _parse_ai_response(self, response_text: str, analysis_type: str) -> AIAnalysisResult:
        """解析AI响应"""
        try:
            # 尝试解析JSON格式响应
            if '```json' in response_text:
                json_str = response_text.split('```json')[1].split('```')[0].strip()
                result_data = json.loads(json_str)
            elif response_text.strip().startswith('{'):
                result_data = json.loads(response_text.strip())
            else:
                # 文本格式响应
                result_data = self._parse_text_response(response_text)
            
            # 转换为标准格式
            peaks = result_data.get('peaks', [])
            phases = result_data.get('phases', [])
            confidence = result_data.get('confidence', 0.7)
            suggestions = result_data.get('suggestions', [])
            
            return AIAnalysisResult(
                peaks=peaks,
                phases=phases,
                confidence=confidence,
                suggestions=suggestions,
                processing_time=0,
                model_used=self.model
            )
            
        except Exception as e:
            # 解析失败，返回默认结果
            return AIAnalysisResult(
                peaks=[],
                phases=[],
                confidence=0.5,
                suggestions=[f"AI分析解析失败: {str(e)}"],
                processing_time=0,
                model_used=self.model
            )
    
    def _parse_text_response(self, text: str) -> Dict:
        """解析文本格式响应"""
        result = {
            'peaks': [],
            'phases': [],
            'suggestions': [],
            'confidence': 0.7
        }
        
        lines = text.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测章节
            if '峰位' in line or '峰检测' in line or 'Peaks' in line:
                current_section = 'peaks'
            elif '物相' in line or '矿物' in line or 'Phases' in line:
                current_section = 'phases'
            elif '建议' in line or '建议' in line or 'Suggestions' in line:
                current_section = 'suggestions'
            elif '置信度' in line or 'Confidence' in line:
                try:
                    if ':' in line:
                        confidence_str = line.split(':')[1].strip()
                        result['confidence'] = float(confidence_str.replace('%', '')) / 100
                except:
                    pass
            
            # 解析峰位
            elif current_section == 'peaks' and ('°' in line or 'theta' in line.lower()):
                try:
                    # 尝试提取峰位信息
                    parts = line.split()
                    position = None
                    intensity = None
                    
                    for part in parts:
                        if '°' in part:
                            position = float(part.replace('°', ''))
                        elif part.replace('.', '').isdigit():
                            num = float(part)
                            if position is None and 5 < num < 90:
                                position = num
                            elif intensity is None and num > 0:
                                intensity = num
                    
                    if position is not None:
                        result['peaks'].append({
                            'position': position,
                            'intensity': intensity or 100,
                            'confidence': 0.8
                        })
                except:
                    pass
            
            # 解析建议
            elif current_section == 'suggestions' and ('•' in line or '-' in line or '*' in line):
                suggestion = line.replace('•', '').replace('-', '').replace('*', '').strip()
                if suggestion:
                    result['suggestions'].append(suggestion)
        
        return result
    
    def _get_fallback_result(self, angles: np.ndarray, intensities: np.ndarray, error: str) -> AIAnalysisResult:
        """获取降级结果（当AI分析失败时）"""
        # 简单的峰检测作为降级方案
        peaks = []
        if len(angles) > 10:
            # 简单的峰值查找
            from scipy import signal
            try:
                peak_indices = signal.find_peaks(intensities, height=np.mean(intensities)*1.5)[0]
                for idx in peak_indices[:10]:  # 最多10个峰
                    peaks.append({
                        'position': float(angles[idx]),
                        'intensity': float(intensities[idx]),
                        'confidence': 0.6
                    })
            except:
                pass
        
        return AIAnalysisResult(
            peaks=peaks,
            phases=[],
            confidence=0.5,
            suggestions=[f"AI分析暂时不可用，使用基础分析。错误: {error}"],
            processing_time=0.1,
            model_used="fallback"
        )
    
    def _peak_analysis_prompt(self) -> str:
        """峰分析提示模板"""
        return """请分析XRD数据中的峰位：

请以JSON格式回复，包含以下信息：
1. 检测到的峰位列表（每个峰包含：position, intensity, confidence）
2. 数据质量评估
3. 分析建议

格式示例：
```json
{
  "peaks": [
    {"position": 26.65, "intensity": 1000, "confidence": 0.9},
    {"position": 20.85, "intensity": 200, "confidence": 0.8}
  ],
  "quality_assessment": "数据质量良好，信噪比高",
  "suggestions": [
    "建议检查20-30°范围的背景噪声",
    "考虑进行背景扣除以改善峰检测"
  ],
  "confidence": 0.85
}
```"""
    
    def _phase_matching_prompt(self) -> str:
        """物相匹配提示模板"""
        return """请根据XRD峰位匹配可能的矿物物相：

请以JSON格式回复，包含以下信息：
1. 匹配的物相列表（每个物相包含：mineral, formula, confidence, matched_peaks）
2. 匹配依据说明
3. 进一步分析建议

常见矿物参考：
- 石英 (Quartz, SiO2): 主要峰位 ~26.65°, 20.85°, 50.15°
- 方解石 (Calcite, CaCO3): 主要峰位 ~29.40°, 39.40°, 43.15°
- 长石 (Feldspar): 复杂峰位，通常在20-30°范围
- 粘土矿物 (Clay minerals): 宽峰，低角度区域

格式示例：
```json
{
  "phases": [
    {
      "mineral": "Quartz",
      "formula": "SiO2",
      "confidence": 0.92,
      "matched_peaks": [0, 1, 4],
      "reasoning": "匹配26.65°和20.85°的强峰"
    }
  ],
  "suggestions": [
    "建议进行Rietveld精修以确认物相比例",
    "考虑可能存在非晶相"
  ],
  "confidence": 0.88
}
```"""
    
    def _quality_assessment_prompt(self) -> str:
        """数据质量评估提示模板"""
        return """请评估XRD数据的质量：

请以JSON格式回复，包含以下信息：
1. 质量评分 (0-1)
2. 主要问题（如果有）
3. 改进建议
4. 数据可用性评估

格式示例：
```json
{
  "quality_score": 0.75,
  "issues": [
    "背景噪声较高",
    "峰形不对称"
  ],
  "suggestions": [
    "建议增加扫描时间以提高信噪比",
    "考虑进行背景扣除处理"
  ],
  "usability": "数据可用于定性分析，定量分析需进一步处理",
  "confidence": 0.8
}
```"""
    
    def _optimization_suggestions_prompt(self) -> str:
        """优化建议提示模板"""
        return """请提供XRD数据分析的优化建议：

请以JSON格式回复，包含以下信息：
1. 分析参数优化建议
2. 数据处理建议
3. 进一步分析方向
4. 潜在问题预警

格式示例：
```json
{
  "parameter_optimization": {
    "peak_detection_sensitivity": "建议使用中等灵敏度",
    "background_subtraction": "建议使用Top-Hat方法",
    "smoothing_window": "建议窗口大小11"
  },
  "data_processing_suggestions": [
    "进行背景扣除以改善峰检测",
    "使用Savitzky-Golay平滑减少噪声"
  ],
  "further_analysis": [
    "建议进行晶粒尺寸分析",
    "考虑进行残余应力分析"
  ],
  "warnings": [
    "注意20-25°范围可能存在仪器伪影"
  ],
  "confidence": 0.85
}
```"""
    
    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        return {
            **self.stats,
            'cache_hit_rate': (
                self.stats['cache_hits'] / max(self.stats['total_requests'], 1)
            ),
            'model': self.model,
            'cache_size': len(list(self.cache_dir.glob('*.pkl')))
        }


# 同步包装器（用于非异步环境）
class SyncOllamaClient:
    """同步版Ollama客户端（包装异步客户端）"""
    
    def __init__(self, **kwargs):
        self.async_client = OptimizedOllamaClient(**kwargs)
        self.loop = None
    
    def __enter__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.loop:
            self.loop.close()
    
    def analyze_xrd_data(self, angles, intensities, analysis_type='full'):
        """同步分析XRD数据"""
        async def _analyze():
            async with self.async_client as client:
                return await client.analyze_xrd_data(angles, intensities, analysis_type)
        
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        return self.loop.run_until_complete(_analyze())
    
    def get_performance_stats(self):
        """获取性能统计"""
        return self.async_client.get_performance_stats()


# 测试函数
async def test_optimized_client():
    """测试优化客户端"""
    # 创建测试数据
    angles = np.linspace(10, 80, 1000)
    intensities = 100 + 500 * np.exp(-((angles - 45) ** 2) / (2 * 5 ** 2))
    intensities += 300 * np.exp(-((angles - 65) ** 2) / (2 * 4 ** 2))
    intensities += np.random.normal(0, 30, 1000)
    
    print("测试优化版Ollama客户端...")
    print(f"数据点数: {len(angles)}")
    print(f"角度范围: {angles.min():.1f}° - {angles.max():.1f}°")
    
    async with OptimizedOllamaClient() as client:
        # 第一次分析（会调用模型）
        print("\n第一次分析（调用模型）...")
        start_time = time.time()
        result = await client.analyze_xrd_data(angles, intensities, 'full')
        elapsed = time.time() - start_time
        
        print(f"处理时间: {elapsed:.2f}秒")
        print(f"置信度: {result.confidence:.2f}")
        print(f"检测到峰数: {len(result.peaks)}")
        print(f"建议数量: {len(result.suggestions)}")
        
        # 第二次分析（应该使用缓存）
        print("\n第二次分析（使用缓存）...")
        start_time = time.time()
        result2 = await client.analyze_xrd_data(angles, intensities, 'full')
        elapsed2 = time.time() - start_time
        
        print(f"处理时间: {elapsed2:.2f}秒 (缓存加速: {elapsed/elapsed2:.1f}x)")
        
        # 显示性能统计
        stats = client.get_performance_stats()
        print("\n性能统计:")
        for key, value in stats.items():
            print(f"  {key}: {value}")


def test_sync_client():
    """测试同步客户端"""
    print("\n测试同步客户端...")
    
    angles = np.linspace(20, 70, 500)
    intensities = 200 + 800 * np.exp(-((angles - 45) ** 2) / (2 * 3 ** 2))
    
    with SyncOllamaClient() as client:
        result = client.analyze_xrd_data(angles, intensities, 'peak_analysis')
        
        print(f"同步分析完成")
        print(f"检测到峰数: {len(result.peaks)}")
        if result.peaks:
            print("前3个峰:")
            for i, peak in enumerate(result.peaks[:3]):
                print(f"  峰{i+1}: {peak['position']:.2f}°, I={peak['intensity']:.0f}")


if __name__ == '__main__':
    # 运行异步测试
    asyncio.run(test_optimized_client())
    
    # 运行同步测试
    test_sync_client()