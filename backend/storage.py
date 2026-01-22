import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from .parser import is_recent_article

logger = logging.getLogger(__name__)

def load_existing_data() -> Dict[str, Dict[str, Any]]:
    """既存の蓄積データを読み込み（タグ別ファイルから）"""
    existing_articles = {}
    tags_dir = Path('data/tags')
    
    if not tags_dir.exists():
        return {}
    
    try:
        # 各タグファイルからデータを読み込み
        for tag_file in tags_dir.glob('*.json'):
            try:
                with open(tag_file, 'r', encoding='utf-8') as f:
                    site_data = json.load(f)
                
                # URLをキーとした辞書に変換（重複チェック用）
                if 'articles_by_date' in site_data:
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

def save_data(articles_by_date: Dict[str, List[Dict[str, Any]]]) -> None:
    """データの保存（タグ別ファイルに分割）"""
    # dataディレクトリとtagsディレクトリの作成
    data_dir = Path('data')
    tags_dir = data_dir / 'tags'
    data_dir.mkdir(exist_ok=True)
    tags_dir.mkdir(exist_ok=True)
    
    # 現在時刻を記録
    timestamp = datetime.now().isoformat()
    
    # 各サイト別にデータを分類
    site_data = {}
    for date_key, articles in articles_by_date.items():
        for article in articles:
            site_name = article.get('site', 'Unknown')
            if site_name not in site_data:
                site_data[site_name] = {
                    'site': site_name,
                    'last_updated': timestamp,
                    'total_articles': 0,
                    'articles_by_date': {}
                }
            
            if date_key not in site_data[site_name]['articles_by_date']:
                site_data[site_name]['articles_by_date'][date_key] = []
            
            site_data[site_name]['articles_by_date'][date_key].append(article)
    
    # 各サイトの記事数を計算してファイル保存
    total_articles = 0
    for site_name, site_info in site_data.items():
        site_total = sum(len(articles) for articles in site_info['articles_by_date'].values())
        site_info['total_articles'] = site_total
        total_articles += site_total
        
        # サイト別ファイルに保存
        site_file = tags_dir / f"{site_name}.json"
        with open(site_file, 'w', encoding='utf-8') as f:
            json.dump(site_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存: {site_name} ({site_total}件)")
    
    # 統計ファイルも作成（互換性のため）
    summary_data = {
        'last_updated': timestamp,
        'total_articles': total_articles,
        'sites_count': len(site_data),
        'articles_by_date': articles_by_date
    }
    
    summary_file = data_dir / 'articles_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"サマリー保存完了: {summary_file}")
    logger.info(f"総記事数: {total_articles}件、サイト数: {len(site_data)}サイト")
    
    # 統計情報を表示
    for date_key, articles in articles_by_date.items():
        logger.info(f"{date_key}: {len(articles)}件")

def merge_articles(new_articles: List[Dict[str, Any]], existing_articles: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """新規記事と既存記事をマージ（重複排除）"""
    merged_articles = []
    added_urls = set()
    
    # 新規記事を追加（重複チェック）
    for article in new_articles:
        url = article.get('url')
        if url and url not in existing_articles and url not in added_urls:
            merged_articles.append(article)
            added_urls.add(url)
        elif url in existing_articles:
            # 既存記事があっても最新情報で更新
            merged_articles.append(article)
            added_urls.add(url)
    
    # 既存記事で1年以内のものを追加
    for url, article in existing_articles.items():
        if url not in added_urls and is_recent_article(article.get('published', ''), days=365):
            merged_articles.append(article)
            added_urls.add(url)
    
    return merged_articles
