import requests
import feedparser
import logging
from typing import List, Dict, Any
from .parser import normalize_article, is_recent_article

logger = logging.getLogger(__name__)

def fetch_rss_feed(feed_url: str, site_name: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """個別RSSフィードの取得と解析"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        logger.info(f"取得開始: {site_name}")
        
        # フィード取得
        response = session.get(feed_url, timeout=30)
        response.raise_for_status()
        
        # フィード解析
        feed = feedparser.parse(response.content)
        
        if feed.bozo:
            logger.warning(f"RSS解析警告: {site_name} - {feed.bozo_exception}")
        
        retention_days = config.get('retention_days', 3650)
        articles = []
        for entry in feed.entries:
            # 記事データの標準化
            article = normalize_article(entry, site_name, config)
            if article and is_recent_article(article['published'], days=retention_days):
                articles.append(article)
        
        logger.info(f"取得完了: {site_name} - {len(articles)}件")
        return articles
        
    except requests.exceptions.RequestException as e:
        logger.error(f"ネットワークエラー ({site_name}): {e}")
        return []
    except Exception as e:
        logger.error(f"予期しないエラー ({site_name}): {e}")
        return []
