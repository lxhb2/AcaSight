"""
Example Plugin: Search Enhancer
搜索结果增强插件 — 自动翻译标题 + 添加标签

演示 AcaSightPlugin 基类的使用方式
"""

from app.services.plugin_system import AcaSightPlugin


class SearchEnhancerPlugin(AcaSightPlugin):
    """搜索结果增强插件"""
    
    async def on_load(self, config: dict) -> None:
        """加载时注册钩子"""
        await super().on_load(config)
        self.register_hook("post_search", self.enhance_search_results)
        self._language = config.get("target_language", "zh")
    
    async def on_enable(self) -> None:
        """启用"""
        pass
    
    async def on_disable(self) -> None:
        """禁用"""
        pass
    
    async def on_unload(self) -> None:
        """卸载"""
        pass
    
    async def enhance_search_results(self, results: list, **kwargs) -> dict:
        """
        post_search 钩子处理器
        
        对搜索结果进行增强:
        1. 为每条结果添加 auto_tags
        2. 统计关键词频率
        """
        if not results:
            return {"enhanced": False, "reason": "no_results"}
        
        all_keywords = []
        for item in results:
            # 简单标签提取
            title = item.get("title", "")
            abstract = item.get("abstract", "")
            
            tags = self._extract_tags(title + " " + abstract)
            item["auto_tags"] = tags
            all_keywords.extend(tags)
        
        # 关键词频率统计
        from collections import Counter
        keyword_freq = Counter(all_keywords).most_common(10)
        
        return {
            "enhanced": True,
            "total_results": len(results),
            "top_keywords": [{"keyword": k, "count": c} for k, c in keyword_freq],
            "target_language": self._language,
        }
    
    def _extract_tags(self, text: str) -> list:
        """简单关键词提取 (演示用)"""
        # 简单实现: 取前5个非停用词
        stopwords = {"the", "a", "an", "of", "in", "and", "for", "to", "with", "on", "at", "by"}
        words = text.lower().split()
        tags = [w.strip(".,;:()[]") for w in words if w.lower() not in stopwords and len(w) > 3]
        return tags[:5]


# 插件入口标记
__acasight_plugin__ = SearchEnhancerPlugin()
