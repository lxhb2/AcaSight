"""
Sci-XRD Pro - AI客户端模块
统一封装Ollama等AI服务
"""

import json
import socket
from typing import Optional, Dict


class OllamaClient:
    """
    Qwen3.5-0.8B AI客户端
    用于XRD图谱分析和智能建议
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen3.5:0.8b"
        self.connected = False
        self._check_connection()
    
    def _check_connection(self):
        """检查Ollama服务连接"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            self.connected = response.status_code == 200
        except:
            self.connected = False
    
    def is_available(self) -> bool:
        """检查AI是否可用"""
        return self.connected
    
    def analyze(self, prompt: str, timeout: int = 60) -> str:
        """
        发送分析请求
        
        Args:
            prompt: 提示词
            timeout: 超时时间（秒）
            
        Returns:
            AI回复
        """
        if not self.connected:
            return "AI服务未连接，请确保Ollama服务正在运行。"
        
        try:
            import requests
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 512
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '无响应')
            else:
                return f"请求失败: {response.status_code}"
                
        except ImportError:
            return "需要安装 requests: pip install requests"
        except socket.timeout:
            return "请求超时"
        except Exception as e:
            return f"错误: {str(e)}"
    
    def explain_peak(self, peak_data: Dict) -> str:
        """
        解释峰位可能的物相
        
        Args:
            peak_data: 峰位数据 {position, d_spacing, intensity}
            
        Returns:
            AI解释
        """
        prompt = f"""作为XRD分析专家，请分析以下峰位数据：
        
峰位信息：
- 2θ角度: {peak_data.get('position', 0):.2f}°
- d间距: {peak_data.get('d_spacing', 0):.4f} Å
- 相对强度: {peak_data.get('intensity', 0):.0f}%

请：
1. 列出可能的矿物/物相
2. 解释判断依据
3. 给出分析建议

简洁回答，控制在200字以内。"""
        
        return self.analyze(prompt)
    
    def suggest_analysis(self, peaks: list, phases: list) -> str:
        """
        提供分析建议
        
        Args:
            peaks: 峰位列表
            phases: 物相列表
            
        Returns:
            建议
        """
        def fmt_peak(idx, p):
            if hasattr(p, 'position'):
                return f"- Peak{idx+1}: 2theta={p.position:.2f}deg, d={p.d_spacing:.4f}A"
            return f"- Peak{idx+1}: 2theta={p.get('position',0):.2f}deg, d={p.get('d_spacing',0):.4f}A"
        
        peaks_info = "\n".join([fmt_peak(i, p) for i, p in enumerate(peaks[:5])])
        
        phases_info = "\n".join([
            f"- {ph.get('name','')} ({ph.get('formula','')}): {ph.get('score',0):.1f}%"
            for ph in phases[:3]
        ])
        
        prompt = f"""作为XRD分析专家，请根据以下分析结果给出建议：

检测到的峰（前5个）：
{peaks_info}

初步匹配的物相（前3个）：
{phases_info}

请给出：
1. 进一步分析建议
2. 需要补充的实验信息
3. 可能的杂质相

简洁回答，控制在200字以内。"""
        
        return self.analyze(prompt)


# 全局AI客户端实例
_ollama_client = None

def get_ai_client() -> OllamaClient:
    """获取AI客户端单例"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
