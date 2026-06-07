import time
import logging
from typing import Dict, List, Any
from .config import load_config, load_category_keywords
from .fetcher import fetch_rss_feed
from .storage import load_existing_data, save_data, merge_articles

logger = logging.getLogger(__name__)

# 既定の保持期間（rss_config.json の retention_days で上書き可能）
DEFAULT_RETENTION_DAYS = 3650

def classify_business_insider_article_by_rss_category(rss_category: str) -> str:
    """Business Insider記事のRSSカテゴリベースでの分類"""
    # RSSカテゴリと対象カテゴリのマッピング（対象外は除外）
    category_mapping = {
        'ビジネス': 'ビジネス',
        'テックニュース': 'テック',
        'サイエンス': 'サイエンス'
    }

    return category_mapping.get(rss_category, None)  # 該当なしはNone

def collect_all_feeds(config: Dict[str, Any], category_keywords: Dict[str, Any]) -> List[Dict[str, Any]]:
    """全フィードの収集（蓄積型・新着順フラットリストを返す）"""
    logger.info("RSS収集を開始します")
    
    # 既存データを読み込み
    existing_articles = load_existing_data()
    logger.info(f"既存記事数: {len(existing_articles)}件")
    
    new_articles = []
    enabled_feeds = [feed for feed in config['rss_feeds'] if feed['enabled']]
    
    for i, feed in enumerate(enabled_feeds):
        # リクエスト間隔を空ける（サーバー負荷軽減）
        if i > 0:
            time.sleep(2)
        
        articles = fetch_rss_feed(feed['url'], feed['name'], config)
        
        # Business Insiderの記事をカテゴリ別に分類
        if feed['name'] == 'Business Insider Japan':
            categorized_articles = []
            for article in articles:
                # まずRSSカテゴリベースで分類を試行
                rss_category = article.get('rss_category', '')
                classified_category = classify_business_insider_article_by_rss_category(rss_category)
                
                # RSSカテゴリベースで分類できない場合は除外
                if classified_category is None:
                    logger.info(f"除外: Business Insider記事 (RSSカテゴリ: {rss_category}) - {article['title'][:50]}...")
                    continue
                
                # 記事をコピーしてカテゴリを更新
                categorized_article = article.copy()
                categorized_article['site'] = f'Business Insider({classified_category})'
                categorized_article['category'] = classified_category
                categorized_articles.append(categorized_article)
            
            new_articles.extend(categorized_articles)
        else:
            new_articles.extend(articles)
    
    # 新規記事と既存記事をマージ（重複排除 + 保持期間で間引き）
    retention_days = config.get('retention_days', DEFAULT_RETENTION_DAYS)
    all_articles = merge_articles(new_articles, existing_articles, retention_days=retention_days)

    # 新着順にソート
    all_articles.sort(key=lambda x: x.get('published', ''), reverse=True)

    logger.info(f"新規記事: {len(new_articles)}件")
    logger.info(f"マージ後総記事数: {len(all_articles)}件（保持期間: {retention_days}日）")
    return all_articles

def main():
    """メイン処理"""
    try:
        # ロギング設定
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        config = load_config()
        category_keywords = load_category_keywords()
        
        all_articles = collect_all_feeds(config, category_keywords)
        save_data(all_articles)
        
        logger.info("RSS収集処理が正常に完了しました")
        
    except KeyboardInterrupt:
        logger.info("処理が中断されました")
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        import sys
        sys.exit(1)
