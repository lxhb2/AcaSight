#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
驱动程序优化模块
提升系统稳定性和性能
"""

import gc
import psutil
import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback
from pathlib import Path
import json

class DriverOptimizer:
    """驱动程序优化器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        
        # 性能监控
        self.monitoring = False
        self.monitor_thread = None
        self.performance_stats = {
            "start_time": datetime.now().isoformat(),
            "cpu_usage": [],
            "memory_usage": [],
            "disk_io": [],
            "network_io": [],
            "gc_stats": []
        }
        
        # 缓存系统
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # 连接池
        self.connection_pool = {}
        
        # 初始化优化
        self._apply_optimizations()
    
    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "memory": {
                "gc_threshold": (700, 10, 10),  # GC阈值
                "enable_auto_gc": True,
                "gc_frequency": 100,  # 每100次操作执行一次GC
                "memory_limit_mb": 1024  # 内存限制
            },
            "performance": {
                "monitor_interval": 5,  # 监控间隔(秒)
                "log_performance": True,
                "performance_log_file": "performance.log"
            },
            "cache": {
                "max_size": 1000,  # 最大缓存条目数
                "ttl_seconds": 3600,  # 缓存存活时间
                "enable_cache": True
            },
            "threading": {
                "max_workers": 4,
                "thread_timeout": 30,  # 线程超时(秒)
                "enable_thread_monitor": True
            },
            "io": {
                "buffer_size": 8192,  # 缓冲区大小
                "enable_compression": True,
                "compression_level": 6
            }
        }
    
    def _apply_optimizations(self):
        """应用系统优化"""
        print("应用系统优化...")
        
        # 1. 内存优化
        self._optimize_memory()
        
        # 2. 线程优化
        self._optimize_threading()
        
        # 3. I/O优化
        self._optimize_io()
        
        # 4. 网络优化
        self._optimize_network()
        
        print("系统优化完成")
    
    def _optimize_memory(self):
        """内存优化"""
        try:
            # 配置垃圾回收
            gc.enable()
            
            # 设置GC阈值
            threshold = self.config["memory"]["gc_threshold"]
            gc.set_threshold(*threshold)
            
            # 禁用调试功能以提升性能
            gc.set_debug(0)
            
            print(f"内存优化: GC阈值设置为 {threshold}")
            
        except Exception as e:
            print(f"内存优化失败: {e}")
    
    def _optimize_threading(self):
        """线程优化"""
        try:
            # 设置线程栈大小（如果需要）
            import threading
            threading.stack_size(2 * 1024 * 1024)  # 2MB栈大小
            
            print("线程优化: 栈大小设置为 2MB")
            
        except Exception as e:
            print(f"线程优化失败: {e}")
    
    def _optimize_io(self):
        """I/O优化"""
        try:
            # 设置文件缓冲区大小
            import io
            io.DEFAULT_BUFFER_SIZE = self.config["io"]["buffer_size"]
            
            print(f"I/O优化: 缓冲区大小设置为 {self.config['io']['buffer_size']} 字节")
            
        except Exception as e:
            print(f"I/O优化失败: {e}")
    
    def _optimize_network(self):
        """网络优化"""
        try:
            # 设置socket超时
            import socket
            socket.setdefaulttimeout(30)  # 30秒超时
            
            print("网络优化: Socket超时设置为 30秒")
            
        except Exception as e:
            print(f"网络优化失败: {e}")
    
    def start_monitoring(self):
        """开始性能监控"""
        if self.monitoring:
            print("性能监控已在运行")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_performance,
            daemon=True
        )
        self.monitor_thread.start()
        
        print("性能监控已启动")
    
    def stop_monitoring(self):
        """停止性能监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        print("性能监控已停止")
    
    def _monitor_performance(self):
        """性能监控循环"""
        interval = self.config["performance"]["monitor_interval"]
        
        while self.monitoring:
            try:
                stats = self._collect_performance_stats()
                self.performance_stats["cpu_usage"].append(stats["cpu"])
                self.performance_stats["memory_usage"].append(stats["memory"])
                self.performance_stats["disk_io"].append(stats["disk"])
                self.performance_stats["network_io"].append(stats["network"])
                self.performance_stats["gc_stats"].append(stats["gc"])
                
                # 记录日志
                if self.config["performance"]["log_performance"]:
                    self._log_performance(stats)
                
                # 检查内存使用
                self._check_memory_usage(stats["memory"])
                
                # 清理旧数据
                self._cleanup_old_stats()
                
            except Exception as e:
                print(f"性能监控错误: {e}")
            
            time.sleep(interval)
    
    def _collect_performance_stats(self) -> Dict[str, Any]:
        """收集性能统计"""
        process = psutil.Process()
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 内存使用
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # 磁盘I/O
        disk_io = psutil.disk_io_counters()
        disk_stats = {
            "read_bytes": disk_io.read_bytes if disk_io else 0,
            "write_bytes": disk_io.write_bytes if disk_io else 0
        }
        
        # 网络I/O
        net_io = psutil.net_io_counters()
        network_stats = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv
        }
        
        # GC统计
        gc_stats = {
            "collected": gc.get_count()[0],
            "uncollectable": gc.get_count()[2],
            "threshold": gc.get_threshold()
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": cpu_percent,
            "memory": memory_mb,
            "disk": disk_stats,
            "network": network_stats,
            "gc": gc_stats
        }
    
    def _check_memory_usage(self, memory_mb: float):
        """检查内存使用"""
        memory_limit = self.config["memory"]["memory_limit_mb"]
        
        if memory_mb > memory_limit * 0.8:  # 超过80%限制
            print(f"警告: 内存使用过高: {memory_mb:.1f} MB (限制: {memory_limit} MB)")
            
            # 触发垃圾回收
            if self.config["memory"]["enable_auto_gc"]:
                self.force_garbage_collection()
                
            # 清理缓存
            self.clear_cache(force=True)
    
    def _log_performance(self, stats: Dict[str, Any]):
        """记录性能日志"""
        try:
            log_file = self.config["performance"]["performance_log_file"]
            
            log_entry = {
                "timestamp": stats["timestamp"],
                "cpu_percent": stats["cpu"],
                "memory_mb": stats["memory"],
                "disk_io": stats["disk"],
                "network_io": stats["network"],
                "gc_stats": stats["gc"]
            }
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            print(f"记录性能日志失败: {e}")
    
    def _cleanup_old_stats(self, keep_hours: int = 24):
        """清理旧的统计数据"""
        try:
            cutoff_time = datetime.now().timestamp() - (keep_hours * 3600)
            
            # 这里可以添加逻辑来清理过时的性能数据
            # 目前只是简单的示例
            
            # 限制数据量
            for key in ["cpu_usage", "memory_usage", "disk_io", "network_io", "gc_stats"]:
                if len(self.performance_stats[key]) > 10000:  # 最多保留10000条
                    self.performance_stats[key] = self.performance_stats[key][-5000:]
                    
        except Exception as e:
            print(f"清理旧统计数据失败: {e}")
    
    def force_garbage_collection(self):
        """强制垃圾回收"""
        try:
            collected = gc.collect()
            print(f"强制垃圾回收: 回收了 {collected} 个对象")
            
            # 获取GC统计
            gc_stats = {
                "generation_0": gc.get_count()[0],
                "generation_1": gc.get_count()[1],
                "generation_2": gc.get_count()[2],
                "collected": collected
            }
            
            return gc_stats
            
        except Exception as e:
            print(f"强制垃圾回收失败: {e}")
            return None
    
    def cache_get(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.config["cache"]["enable_cache"]:
            self.cache_misses += 1
            return None
        
        if key in self.cache:
            entry = self.cache[key]
            
            # 检查是否过期
            if time.time() - entry["timestamp"] < self.config["cache"]["ttl_seconds"]:
                self.cache_hits += 1
                return entry["data"]
            else:
                # 过期，删除
                del self.cache[key]
        
        self.cache_misses += 1
        return None
    
    def cache_set(self, key: str, data: Any):
        """设置缓存数据"""
        if not self.config["cache"]["enable_cache"]:
            return
        
        # 检查缓存大小
        if len(self.cache) >= self.config["cache"]["max_size"]:
            self._evict_cache()
        
        self.cache[key] = {
            "data": data,
            "timestamp": time.time(),
            "access_count": 0
        }
    
    def _evict_cache(self):
        """缓存淘汰策略"""
        try:
            # 使用LRU策略
            if not self.cache:
                return
            
            # 找到最久未访问的条目
            oldest_key = None
            oldest_time = float('inf')
            
            for key, entry in self.cache.items():
                if entry["timestamp"] < oldest_time:
                    oldest_time = entry["timestamp"]
                    oldest_key = key
            
            if oldest_key:
                del self.cache[oldest_key]
                print(f"缓存淘汰: 移除了键 '{oldest_key}'")
                
        except Exception as e:
            print(f"缓存淘汰失败: {e}")
    
    def clear_cache(self, force: bool = False):
        """清空缓存"""
        try:
            if force or not self.config["cache"]["enable_cache"]:
                self.cache.clear()
                self.cache_hits = 0
                self.cache_misses = 0
                print("缓存已清空")
            else:
                # 只清理过期的
                current_time = time.time()
                expired_keys = [
                    key for key, entry in self.cache.items()
                    if current_time - entry["timestamp"] > self.config["cache"]["ttl_seconds"]
                ]
                
                for key in expired_keys:
                    del self.cache[key]
                
                if expired_keys:
                    print(f"清理了 {len(expired_keys)} 个过期缓存条目")
                    
        except Exception as e:
            print(f"清空缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self.cache),
            "max_size": self.config["cache"]["max_size"],
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "hit_rate": hit_rate,
            "ttl_seconds": self.config["cache"]["ttl_seconds"]
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        try:
            # 计算平均统计
            def calculate_average(stats_list, key=None):
                if not stats_list:
                    return 0
                
                if key:
                    values = [s[key] for s in stats_list if key in s]
                else:
                    values = stats_list
                
                return sum(values) / len(values) if values else 0
            
            # CPU使用率
            avg_cpu = calculate_average(self.performance_stats["cpu_usage"])
            max_cpu = max(self.performance_stats["cpu_usage"]) if self.performance_stats["cpu_usage"] else 0
            
            # 内存使用
            avg_memory = calculate_average(self.performance_stats["memory_usage"])
            max_memory = max(self.performance_stats["memory_usage"]) if self.performance_stats["memory_usage"] else 0
            
            # 磁盘I/O
            total_disk_read = sum(s["read_bytes"] for s in self.performance_stats["disk_io"])
            total_disk_write = sum(s["write_bytes"] for s in self.performance_stats["disk_io"])
            
            # 网络I/O
            total_network_sent = sum(s["bytes_sent"] for s in self.performance_stats["network_io"])
            total_network_recv = sum(s["bytes_recv"] for s in self.performance_stats["network_io"])
            
            # 运行时间
            start_time = datetime.fromisoformat(self.performance_stats["start_time"])
            uptime = (datetime.now() - start_time).total_seconds()
            
            report = {
                "system_info": {
                    "start_time": self.performance_stats["start_time"],
                    "uptime_seconds": uptime,
                    "uptime_human": self._format_seconds(uptime),
                    "monitoring_enabled": self.monitoring
                },
                "performance": {
                    "cpu": {
                        "average": avg_cpu,
                        "maximum": max_cpu,
                        "unit": "%"
                    },
                    "memory": {
                        "average": avg_memory,
                        "maximum": max_memory,
                        "unit": "MB",
                        "limit": self.config["memory"]["memory_limit_mb"]
                    },
                    "disk": {
                        "total_read": total_disk_read,
                        "total_write": total_disk_write,
                        "unit": "bytes"
                    },
                    "network": {
                        "total_sent": total_network_sent,
                        "total_recv": total_network_recv,
                        "unit": "bytes"
                    }
                },
                "cache": self.get_cache_stats(),
                "gc": {
                    "total_collections": len(self.performance_stats["gc_stats"]),
                    "last_collection": self.performance_stats["gc_stats"][-1] if self.performance_stats["gc_stats"] else None
                }
            }
            
            return report
            
        except Exception as e:
            print(f"生成性能报告失败: {e}")
            return {"error": str(e)}
    
    def _format_seconds(self, seconds: float) -> str:
        """格式化秒数为可读字符串"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def optimize_query(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """优化数据库查询"""
        try:
            # 这里可以添加查询优化逻辑
            # 例如：查询重写、索引提示、缓存策略等
            
            optimized = {
                "original_query": query,
                "optimized_query": query,  # 实际应用中这里会有优化
                "optimizations_applied": [],
                "estimated_savings": "N/A"
            }
            
            # 简单的查询分析
            query_lower = query.lower()
            
            if "select *" in query_lower:
                optimized["optimizations_applied"].append("避免使用 SELECT *")
                optimized["estimated_savings"] = "减少数据传输量"
            
            if "join" in query_lower and "index" not in query_lower:
                optimized["optimizations_applied"].append("建议添加索引")
                optimized["estimated_savings"] = "提升连接性能"
            
            return optimized
            
        except Exception as e:
            print(f"查询优化失败: {e}")
            return {"error": str(e)}
    
    def shutdown(self):
        """关闭优化器"""
        print("关闭驱动程序优化器...")
        
        # 停止监控
        self.stop_monitoring()
        
        # 清理缓存
        self.clear_cache(force=True)
        
        # 强制垃圾回收
        self.force_garbage_collection()
