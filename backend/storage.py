import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone
from .parser import is_recent_article

logger = logging.getLogger(__name__)

# 配信用データの配置先（Astroが public/ を dist/ にそのままコピーするため、
# ビルド時の fs 読み込みと実行時の fetch の両方に使える）
DATA_DIR = Path('public/data')
TAGS_DIR = DATA_DIR / 'tags'


def _jst():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Asia/Tokyo")
    except ImportError:
        return timezone(timedelta(hours=9))


def load_existing_data() -> Dict[str, Dict[str, Any]]:
    """既存の蓄積データを読み込み（タグ別ファイルから / 新旧フォーマット両対応）"""
    existing_articles: Dict[str, Dict[str, Any]] = {}

    if not TAGS_DIR.exists():
        return {}

    try:
        for tag_file in TAGS_DIR.glob('*.json'):
            try:
                with open(tag_file, 'r', encoding='utf-8') as f:
                    site_data = json.load(f)

                # 新フォーマット: フラットな articles 配列
                if isinstance(site_data.get('articles'), list):
                    for article in site_data['articles']:
                        if 'url' in article:
                            existing_articles[article['url']] = article
                # 旧フォーマット: articles_by_date（移行直後の1回のみ通過）
                elif 'articles_by_date' in site_data:
                    for date_articles in site_data['articles_by_date'].values():
                        for article in date_articles:
                            if 'url' in article:
                                existing_articles[article['url']] = article

            except Exception as e:
                logger.warning(f"タグファイル読み込み失敗 {tag_file.name}: {e}")
                continue

        logger.info(f"既存データ読み込み完了: {len(existing_articles)}件")
        return existing_articles

    except Exception as e:
        logger.warning(f"既存データの読み込み失敗: {e}")
        return {}


def _sort_key(article: Dict[str, Any]) -> str:
    return article.get('published', '')


def save_data(all_articles: List[Dict[str, Any]]) -> None:
    """データの保存（タグ別フラット配列 + 軽量な統計/検索インデックス）"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TAGS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()

    # サイト別に分類
    by_site: Dict[str, List[Dict[str, Any]]] = {}
    for article in all_articles:
        site_name = article.get('site', 'Unknown')
        by_site.setdefault(site_name, []).append(article)

    # タグ別ファイルを保存（新着順フラット配列）
    total_articles = 0
    per_site_counts: Dict[str, int] = {}
    for site_name, articles in by_site.items():
        articles.sort(key=_sort_key, reverse=True)
        total_articles += len(articles)
        per_site_counts[site_name] = len(articles)

        site_info = {
            'site': site_name,
            'last_updated': timestamp,
            'total_articles': len(articles),
            'articles': articles,
        }
        site_file = TAGS_DIR / f"{site_name}.json"
        with open(site_file, 'w', encoding='utf-8') as f:
            json.dump(site_info, f, ensure_ascii=False, indent=2)
        logger.info(f"保存: {site_name} ({len(articles)}件)")

    # 期間別カウント（本日/昨日/一昨日）を JST で算出（統計表示用）
    period_counts = _count_by_period(all_articles)

    # 統計ファイル（極小・旧 articles_summary.json の置き換え）
    stats = {
        'last_updated': timestamp,
        'total_articles': total_articles,
        'sites_count': len(by_site),
        'per_site': per_site_counts,
        'by_period': period_counts,
    }
    with open(DATA_DIR / 'stats.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # 検索インデックス（全履歴・軽量: title/url/site/published のみ、新着順1行1記事）
    index_articles = sorted(all_articles, key=_sort_key, reverse=True)
    with open(DATA_DIR / 'search-index.jsonl', 'w', encoding='utf-8') as f:
        for a in index_articles:
            f.write(json.dumps({
                'title': a.get('title', ''),
                'url': a.get('url', ''),
                'site': a.get('site', ''),
                'published': a.get('published', ''),
            }, ensure_ascii=False))
            f.write('\n')

    logger.info(f"統計保存完了: 総記事数 {total_articles}件 / {len(by_site)}サイト")
    for period, count in period_counts.items():
        logger.info(f"{period}: {count}件")


def _count_by_period(articles: List[Dict[str, Any]]) -> Dict[str, int]:
    """本日/昨日/一昨日の件数を JST で算出"""
    jst = _jst()
    today = datetime.now(jst).date()
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)
    counts = {'本日': 0, '昨日': 0, '一昨日': 0}

    for article in articles:
        try:
            dt = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            d = dt.astimezone(jst).date()
            if d == today:
                counts['本日'] += 1
            elif d == yesterday:
                counts['昨日'] += 1
            elif d == day_before:
                counts['一昨日'] += 1
        except Exception:
            continue
    return counts


def merge_articles(new_articles: List[Dict[str, Any]],
                   existing_articles: Dict[str, Dict[str, Any]],
                   retention_days: int = 365) -> List[Dict[str, Any]]:
    """新規記事と既存記事をマージ（重複排除 + 保持期間で間引き）"""
    merged_articles: List[Dict[str, Any]] = []
    added_urls = set()

    # 新規記事を追加（既存があれば最新情報で更新）
    for article in new_articles:
        url = article.get('url')
        if url and url not in added_urls:
            merged_articles.append(article)
            added_urls.add(url)

    # 既存記事で保持期間内のものを追加
    for url, article in existing_articles.items():
        if url not in added_urls and is_recent_article(article.get('published', ''), days=retention_days):
            merged_articles.append(article)
            added_urls.add(url)

    return merged_articles
