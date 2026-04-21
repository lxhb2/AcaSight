#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理逻辑模块
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

class BatchProcessor:
    """批处理器"""
    
    def __init__(self, xrd_analyzer, max_workers: int = 4):
        self.xrd_analyzer = xrd_analyzer
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 批处理状态跟踪
        self.batch_status = {}
    
    async def process_batch(self, file_paths: List[str], batch_id: str) -> Dict[str, Any]:
        """处理批量文件"""
        try:
            start_time = datetime.now()
            
            # 初始化批处理状态
            self.batch_status[batch_id] = {
                "id": batch_id,
                "start_time": start_time.isoformat(),
                "total_files": len(file_paths),
                "processed_files": 0,
                "successful_files": 0,
                "failed_files": 0,
                "current_file": None,
                "progress": 0.0,
                "results": [],
                "errors": []
            }
            
            print(f"开始批处理 {batch_id}: {len(file_paths)} 个文件")
            
            # 使用线程池并行处理
            results = []
            with self.executor as executor:
                # 提交所有任务
                future_to_file = {
                    executor.submit(self._process_single_file, file_path, batch_id): file_path
                    for file_path in file_paths
                }
                
                # 收集结果
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    
                    try:
                        result = future.result()
                        results.append(result)
                        
                        # 更新状态
                        self._update_batch_status(batch_id, result)
                        
                    except Exception as e:
                        error_result = {
                            "file_path": file_path,
                            "success": False,
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        }
                        results.append(error_result)
                        
                        # 更新错误状态
                        self.batch_status[batch_id]["failed_files"] += 1
                        self.batch_status[batch_id]["errors"].append({
                            "file": file_path,
                            "error": str(e)
                        })
            
            # 计算总耗时
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # 生成批处理报告
            batch_report = self._generate_batch_report(batch_id, results, elapsed)
            
            # 保存批处理结果
            self._save_batch_results(batch_id, batch_report)
            
            # 清理状态（保留最近的一些记录）
            self._cleanup_old_batches()
            
            print(f"批处理完成 {batch_id}: 耗时 {elapsed:.2f}秒")
            
            return batch_report
            
        except Exception as e:
            print(f"批处理失败: {e}")
            traceback.print_exc()
            
            error_report = {
                "batch_id": batch_id,
                "success": False,
                "error": str(e),
                "processed_files": 0,
                "total_files": len(file_paths),
                "processing_time": 0.0
            }
            
            return error_report
    
    def _process_single_file(self, file_path: str, batch_id: str) -> Dict[str, Any]:
        """处理单个文件（在单独的线程中运行）"""
        try:
            # 更新当前处理文件
            self.batch_status[batch_id]["current_file"] = Path(file_path).name
            
            print(f"处理文件: {file_path}")
            
            # 使用同步方式调用分析器（因为在线程中）
            # 注意：这里需要确保xrd_analyzer的方法是线程安全的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 执行分析
                result = loop.run_until_complete(
                    self.xrd_analyzer.analyze_file(file_path)
                )
                
                result.update({
                    "file_path": file_path,
                    "filename": Path(file_path).name,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                })
                
                return result
                
            finally:
                loop.close()
                
        except Exception as e:
            print(f"处理文件失败 {file_path}: {e}")
            
            return {
                "file_path": file_path,
                "filename": Path(file_path).name,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _update_batch_status(self, batch_id: str, result: Dict[str, Any]):
        """更新批处理状态"""
        if batch_id not in self.batch_status:
            return
        
        status = self.batch_status[batch_id]
        status["processed_files"] += 1
        
        if result.get("success", False):
            status["successful_files"] += 1
            status["results"].append({
                "file": result["filename"],
                "success": True,
                "peak_count": len(result.get("analysis_results", {}).get("peaks", {}).get("angles", [])),
                "phase_count": len(result.get("analysis_results", {}).get("matched_phases", [])),
                "processing_time": result.get("processing_time", 0.0)
            })
        else:
            status["failed_files"] += 1
            status["errors"].append({
                "file": result.get("filename", "unknown"),
                "error": result.get("error", "unknown error")
            })
        
        # 计算进度
        if status["total_files"] > 0:
            status["progress"] = (status["processed_files"] / status["total_files"]) * 100
        
        # 更新当前文件
        if status["processed_files"] >= status["total_files"]:
            status["current_file"] = None
        else:
            # 这里可以添加逻辑来获取下一个文件名
            pass
    
    def _generate_batch_report(self, batch_id: str, results: List[Dict[str, Any]], 
                              elapsed_time: float) -> Dict[str, Any]:
        """生成批处理报告"""
        successful_results = [r for r in results if r.get("success", False)]
        failed_results = [r for r in results if not r.get("success", False)]
        
        # 统计信息
        total_peaks = sum(
            len(r.get("analysis_results", {}).get("peaks", {}).get("angles", []))
            for r in successful_results
        )
        
        total_phases = sum(
            len(r.get("analysis_results", {}).get("matched_phases", []))
            for r in successful_results
        )
        
        # 平均处理时间
        avg_processing_time = (
            sum(r.get("processing_time", 0.0) for r in successful_results) / 
            len(successful_results) if successful_results else 0.0
        )
        
        # 常见物相统计
        common_phases = self._analyze_common_phases(successful_results)
        
        # 生成报告
        report = {
            "batch_id": batch_id,
            "summary": {
                "total_files": len(results),
                "successful_files": len(successful_results),
                "failed_files": len(failed_results),
                "success_rate": (len(successful_results) / len(results)) * 100 if results else 0,
                "total_processing_time": elapsed_time,
                "avg_processing_time": avg_processing_time,
                "total_peaks_detected": total_peaks,
                "total_phases_matched": total_phases,
                "avg_peaks_per_file": total_peaks / len(successful_results) if successful_results else 0,
                "avg_phases_per_file": total_phases / len(successful_results) if successful_results else 0
            },
            "file_results": [
                {
                    "filename": r.get("filename", "unknown"),
                    "success": r.get("success", False),
                    "peak_count": len(r.get("analysis_results", {}).get("peaks", {}).get("angles", [])),
                    "phase_count": len(r.get("analysis_results", {}).get("matched_phases", [])),
                    "top_phase": (
                        r.get("analysis_results", {}).get("matched_phases", [{}])[0].get("name", "无匹配")
                        if r.get("analysis_results", {}).get("matched_phases")
                        else "无匹配"
                    ),
                    "processing_time": r.get("processing_time", 0.0),
                    "error": r.get("error") if not r.get("success") else None
                }
                for r in results
            ],
            "common_phases": common_phases,
            "performance_metrics": {
                "files_per_second": len(results) / elapsed_time if elapsed_time > 0 else 0,
                "peaks_per_second": total_peaks / elapsed_time if elapsed_time > 0 else 0,
                "phases_per_second": total_phases / elapsed_time if elapsed_time > 0 else 0
            },
            "recommendations": self._generate_batch_recommendations(successful_results, failed_results),
            "timestamp": datetime.now().isoformat()
        }
        
        return report
    
    def _analyze_common_phases(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析常见物相"""
        phase_counter = {}
        
        for result in results:
            phases = result.get("analysis_results", {}).get("matched_phases", [])
            for phase in phases[:3]:  # 只考虑前3个匹配
                phase_name = phase.get("name", "")
                if phase_name:
                    phase_counter[phase_name] = phase_counter.get(phase_name, 0) + 1
        
        # 按出现频率排序
        common_phases = [
            {
                "phase_name": phase_name,
                "occurrence_count": count,
                "occurrence_percentage": (count / len(results)) * 100 if results else 0
            }
            for phase_name, count in sorted(
                phase_counter.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]  # 取前10个
        ]
        
        return common_phases
    
    def _generate_batch_recommendations(self, successful_results: List[Dict[str, Any]], 
                                       failed_results: List[Dict[str, Any]]) -> List[str]:
        """生成批处理建议"""
        recommendations = []
        
        # 基于成功率的建议
        total_files = len(successful_results) + len(failed_results)
        success_rate = (len(successful_results) / total_files) * 100 if total_files > 0 else 0
        
        if success_rate < 50:
            recommendations.append("处理成功率较低，建议检查文件格式或数据质量。")
        elif success_rate < 80:
            recommendations.append("处理成功率中等，部分文件可能需要手动检查。")
        else:
            recommendations.append("处理成功率很高，批处理效果良好。")
        
        # 基于处理时间的建议
        if successful_results:
            processing_times = [r.get("processing_time", 0.0) for r in successful_results]
            avg_time = sum(processing_times) / len(processing_times)
            max_time = max(processing_times)
            
            if max_time > avg_time * 3:
                recommendations.append("部分文件处理时间异常，建议检查这些文件的数据复杂度。")
        
        # 基于物相匹配的建议
        if successful_results:
            phase_counts = [
                len(r.get("analysis_results", {}).get("matched_phases", []))
                for r in successful_results
            ]
            avg_phases = sum(phase_counts) / len(phase_counts)
            
            if avg_phases < 1:
                recommendations.append("平均匹配物相较少，可能需要调整匹配参数或检查数据库覆盖度。")
            elif avg_phases > 10:
                recommendations.append("匹配到较多物相，可能需要更严格的匹配阈值。")
        
        return recommendations
    
    def _save_batch_results(self, batch_id: str, batch_report: Dict[str, Any]):
        """保存批处理结果"""
        try:
            # 创建结果目录
            results_dir = Path("batch_results")
            results_dir.mkdir(exist_ok=True)
            
            # 保存JSON报告
            report_file = results_dir / f"{batch_id}_report.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(batch_report, f, ensure_ascii=False, indent=2)
            
            # 保存CSV摘要
            csv_file = results_dir / f"{batch_id}_summary.csv"
            self._save_batch_csv(csv_file, batch_report)
            
            print(f"批处理结果已保存: {report_file}, {csv_file}")
            
        except Exception as e:
            print(f"保存批处理结果失败: {e}")
    
    def _save_batch_csv(self, csv_file: Path, batch_report: Dict[str, Any]):
        """保存CSV摘要"""
        import csv
        
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # 写入摘要
            writer.writerow(["批处理摘要", f"批处理ID: {batch_report['batch_id']}"])
            writer.writerow(["生成时间", batch_report["timestamp"]])
            writer.writerow([])
            
            # 写入统计信息
            writer.writerow(["统计信息"])
            summary = batch_report["summary"]
            writer.writerow(["总文件数", summary["total_files"]])
            writer.writerow(["成功文件数", summary["successful_files"]])
            writer.writerow(["失败文件数", summary["failed_files"]])
            writer.writerow(["成功率", f"{summary['success_rate']:.1f}%"])
            writer.writerow(["总处理时间", f"{summary['total_processing_time']:.2f}秒"])
            writer.writerow(["平均处理时间", f"{summary['avg_processing_time']:.2f}秒"])
            writer.writerow(["总检测峰数", summary["total_peaks_detected"]])
            writer.writerow(["总匹配物相数", summary["total_phases_matched"]])
            writer.writerow([])
            
            # 写入文件结果
            writer.writerow(["文件详细结果"])
            writer.writerow(["文件名", "状态", "峰数", "物相数", "主要物相", "处理时间(秒)", "错误信息"])
            
            for file_result in batch_report["file_results"]:
                status = "成功" if file_result["success"] else "失败"
                error = file_result.get("error", "")
                writer.writerow([
                    file_result["filename"],
                    status,
                    file_result["peak_count"],
                    file_result["phase_count"],
                    file_result["top_phase"],
                    f"{file_result['processing_time']:.2f}",
                    error
                ])
            
            writer.writerow([])
            
            # 写入常见物相
            if batch_report["common_phases"]:
                writer.writerow(["常见物相统计"])
                writer.writerow(["物相名称", "出现次数", "出现频率(%)"])
                
                for phase in batch_report["common_phases"]:
                    writer.writerow([
                        phase["phase_name"],
                        phase["occurrence_count"],
                        f"{phase['occurrence_percentage']:.1f}"
                    ])
    
    def _cleanup_old_batches(self, keep_count: int = 10):
        """清理旧的批处理状态"""
        if len(self.batch_status) > keep_count:
            # 按开始时间排序，保留最新的
            sorted_batches = sorted(
                self.batch_status.items(),
                key=lambda x: x[1].get("start_time", ""),
                reverse=True
            )
            
            # 删除旧的
            for batch_id, _ in sorted_batches[keep_count:]:
                del self.batch_status[batch_id]
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """获取批处理状态"""
        return self.batch_status.get(batch_id)
    
    def get_all_batch_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有批处理状态"""
        return self.batch_status.copy()
    
    def stop(self):
        """停止批处理器"""
        self.executor.shutdown(wait=True)
        print("批处理器已停止")