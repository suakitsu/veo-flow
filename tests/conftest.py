"""
pytest 配置：确保项目根目录在 sys.path 中
"""
import sys
from pathlib import Path

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
