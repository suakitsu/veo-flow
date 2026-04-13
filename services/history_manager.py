"""
History Manager - 线程安全的生成历史记录与统计
所有路由和生成器通过此模块读写 history.json
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from config import BASE_DIR

HISTORY_FILE = BASE_DIR / 'history.json'
_lock = threading.Lock()

# 模型单价（美元/秒或美元/张）
MODEL_COST = {
    'veo-2.0-generate-001': 0.50,
    'veo-3.0-generate-001': 0.40,
    'veo-3.0-fast-generate-001': 0.20,
    'veo-3.1-generate-001': 0.40,
    'veo-3.1-fast-generate-001': 0.20,
    'imagen-3.0-generate-002': 0.04,
    'imagen-3.0-fast-generate-001': 0.02,
}


def _load() -> list:
    """加载历史列表（始终返回 list）"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 兼容旧格式 {"history": [...], "total_cost": ...}
            if isinstance(data, dict):
                return data.get('history', [])
            if isinstance(data, list):
                return data
        except Exception:
            # 文件损坏，备份
            bak = HISTORY_FILE.with_suffix('.json.bak')
            try:
                HISTORY_FILE.rename(bak)
            except OSError:
                pass
    return []


def _save(records: list):
    """保存历史列表"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def record(task_id: str, prompt: str, model: str, model_id: str,
           duration: int, mode: str, ratio: str, status: str,
           elapsed: float = 0.0) -> dict:
    """记录一次生成，保存到 history.json，返回记录 dict"""
    cost = MODEL_COST.get(model_id, 0.015) * max(duration, 1)
    entry = {
        'id': task_id,
        'prompt': prompt,
        'model': model,
        'model_id': model_id,
        'duration': duration,
        'mode': mode,
        'ratio': ratio,
        'status': status,
        'cost': round(cost, 4),
        'elapsed': round(elapsed, 1),
        'created_at': datetime.now().isoformat(),
    }
    with _lock:
        history = _load()
        history.append(entry)
        if len(history) > 500:
            history = history[-500:]
        _save(history)
    return entry


def get_history(limit: int = 50, offset: int = 0) -> dict:
    """取历史（倒序），返回前端期望格式"""
    history = _load()
    history = list(reversed(history))
    return {
        'total': len(history),
        'history': history[offset: offset + limit],
    }


def get_stats() -> dict:
    """计算统计数据"""
    history = _load()
    total = len(history)
    completed = [r for r in history if r.get('status') == 'completed']
    total_cost = sum(r.get('cost', 0) for r in history)
    avg_time = (
        sum(r.get('elapsed', 0) for r in completed) / len(completed)
        if completed else 0
    )
    return {
        'total_cost': round(total_cost, 4),
        'total_generations': total,
        'success_rate': round(len(completed) / total * 100, 1) if total else 0,
        'avg_time': round(avg_time, 1),
    }


def clear():
    """清空所有历史"""
    with _lock:
        _save([])
