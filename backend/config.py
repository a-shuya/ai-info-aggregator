import json
import logging
import sys
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_config(config_file: str = "rss_config.json") -> Dict[str, Any]:
    """設定ファイルの読み込み"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"設定ファイル {config_file} が見つかりません")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"設定ファイル {config_file} の形式が正しくありません")
        sys.exit(1)

def load_category_keywords() -> Dict[str, Any]:
    """カテゴリキーワード設定の読み込み"""
    try:
        with open('category_keywords.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("category_keywords.json が見つかりません。カテゴリ分類を無効にします")
        return {}
    except json.JSONDecodeError:
        logger.warning("category_keywords.json の形式が正しくありません。カテゴリ分類を無効にします")
        return {}
