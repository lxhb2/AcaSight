"""
工作区状态持久化服务 (方向T.1)

功能:
1. 工作区状态保存 (save)
2. 工作区状态恢复 (restore)
3. 工作区列表 (list)
4. 工作区删除 (delete)
5. 自动保存支持 (auto-save)
6. 快照管理 (snapshots)

存储: JSON 文件 (data/workspace_states/)
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()

# 默认存储目录
DEFAULT_STATES_DIR = os.path.join(os.getcwd(), "data", "workspace_states")


class WorkspaceStateService:
    """
    工作区状态持久化服务
    
    存储结构:
    data/workspace_states/
    ├── {workspace_id}/
    │   ├── meta.json           # 元数据 (名称/创建时间/修改时间/标签)
    │   ├── latest.json         # 最新状态快照
    │   └── snapshots/
    │       ├── {timestamp}.json  # 历史快照
    │       └── ...
    """
    
    def __init__(self, states_dir: Optional[str] = None):
        self._states_dir = states_dir or DEFAULT_STATES_DIR
        os.makedirs(self._states_dir, exist_ok=True)
    
    def save(self, workspace_id: str, state: Dict[str, Any], name: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict:
        """
        保存工作区状态
        
        Args:
            workspace_id: 工作区ID
            state: 状态数据 (任意 JSON-serializable dict)
            name: 工作区名称
            tags: 标签
        
        Returns:
            保存结果
        """
        workspace_dir = os.path.join(self._states_dir, workspace_id)
        os.makedirs(workspace_dir, exist_ok=True)
        os.makedirs(os.path.join(workspace_dir, "snapshots"), exist_ok=True)
        
        now = time.time()
        
        # 更新元数据
        meta_path = os.path.join(workspace_dir, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["updated_at"] = now
            meta["update_count"] = meta.get("update_count", 0) + 1
            if name:
                meta["name"] = name
            if tags:
                meta["tags"] = tags
        else:
            meta = {
                "id": workspace_id,
                "name": name or f"Workspace {workspace_id[:8]}",
                "created_at": now,
                "updated_at": now,
                "update_count": 1,
                "tags": tags or [],
            }
        
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        # 保存最新状态
        state_with_meta = {
            "workspace_id": workspace_id,
            "saved_at": now,
            "state": state,
        }
        
        latest_path = os.path.join(workspace_dir, "latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(state_with_meta, f, ensure_ascii=False, indent=2)
        
        # 创建快照 (带时间戳)
        snapshot_path = os.path.join(workspace_dir, "snapshots", f"{int(now)}.json")
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(state_with_meta, f, ensure_ascii=False, indent=2)
        
        # 清理旧快照 (保留最近10个)
        self._cleanup_old_snapshots(workspace_dir, max_snapshots=10)
        
        logger.info("Workspace state saved", workspace_id=workspace_id)
        return {
            "success": True,
            "workspace_id": workspace_id,
            "saved_at": now,
            "update_count": meta["update_count"],
        }
    
    def restore(self, workspace_id: str, snapshot_timestamp: Optional[float] = None) -> Optional[Dict]:
        """
        恢复工作区状态
        
        Args:
            workspace_id: 工作区ID
            snapshot_timestamp: 快照时间戳 (None=最新)
        
        Returns:
            状态数据 或 None
        """
        workspace_dir = os.path.join(self._states_dir, workspace_id)
        if not os.path.exists(workspace_dir):
            return None
        
        if snapshot_timestamp:
            # 恢复特定快照
            snapshot_path = os.path.join(workspace_dir, "snapshots", f"{int(snapshot_timestamp)}.json")
            if not os.path.exists(snapshot_path):
                return None
            with open(snapshot_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # 恢复最新状态
            latest_path = os.path.join(workspace_dir, "latest.json")
            if not os.path.exists(latest_path):
                return None
            with open(latest_path, "r", encoding="utf-8") as f:
                return json.load(f)
    
    def list_workspaces(self, tag: Optional[str] = None) -> List[Dict]:
        """
        列出所有工作区
        
        Args:
            tag: 按标签过滤
        """
        workspaces = []
        
        if not os.path.exists(self._states_dir):
            return workspaces
        
        for entry in os.listdir(self._states_dir):
            meta_path = os.path.join(self._states_dir, entry, "meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                
                if tag and tag not in meta.get("tags", []):
                    continue
                
                workspaces.append(meta)
        
        # 按更新时间倒序
        workspaces.sort(key=lambda w: w.get("updated_at", 0), reverse=True)
        return workspaces
    
    def delete(self, workspace_id: str) -> bool:
        """删除工作区"""
        import shutil
        workspace_dir = os.path.join(self._states_dir, workspace_id)
        if not os.path.exists(workspace_dir):
            return False
        
        shutil.rmtree(workspace_dir)
        logger.info("Workspace state deleted", workspace_id=workspace_id)
        return True
    
    def get_snapshots(self, workspace_id: str) -> List[Dict]:
        """获取工作区快照列表"""
        snapshots_dir = os.path.join(self._states_dir, workspace_id, "snapshots")
        if not os.path.exists(snapshots_dir):
            return []
        
        snapshots = []
        for filename in os.listdir(snapshots_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(snapshots_dir, filename)
                timestamp = float(filename.replace(".json", ""))
                size = os.path.getsize(filepath)
                snapshots.append({
                    "timestamp": timestamp,
                    "filename": filename,
                    "size_bytes": size,
                })
        
        snapshots.sort(key=lambda s: s["timestamp"], reverse=True)
        return snapshots
    
    def _cleanup_old_snapshots(self, workspace_dir: str, max_snapshots: int = 10):
        """清理旧快照，保留最近N个"""
        snapshots_dir = os.path.join(workspace_dir, "snapshots")
        if not os.path.exists(snapshots_dir):
            return
        
        files = sorted(
            [f for f in os.listdir(snapshots_dir) if f.endswith(".json")],
            reverse=True,
        )
        
        # 删除多余的旧快照
        for old_file in files[max_snapshots:]:
            os.remove(os.path.join(snapshots_dir, old_file))


# Singleton
_workspace_state_service: Optional[WorkspaceStateService] = None


def get_workspace_state_service() -> WorkspaceStateService:
    global _workspace_state_service
    if _workspace_state_service is None:
        _workspace_state_service = WorkspaceStateService()
    return _workspace_state_service
