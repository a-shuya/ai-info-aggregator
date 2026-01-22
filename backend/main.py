import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from .config import load_config, load_category_keywords
from .fetcher import fetch_rss_feed
from .storage import load_existing_data, save_data, merge_articles

logger = logging.getLogger(__name__)

def classify_business_insider_article_by_rss_category(rss_category: str) -> str:
    """Business Insider記事のRSSカテゴリベースでの分類"""
    # RSSカテゴリと対象カテゴリのマッピング（対象外は除外）
    category_mapping = {
        'ビジネス': 'ビジネス',
        'テックニュース': 'テック',
        'サイエンス': 'サイエンス'
    }
    
    return category_mapping.get(rss_category, None)  # 該当なしはNone

def group_articles_by_date(articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """記事を日付別にグループ化（全期間対応）"""
    try:
        from zoneinfo import ZoneInfo
        jst = ZoneInfo("Asia/Tokyo")
    except ImportError:
        # Python 3.8以前の場合
        from datetime import timezone
        jst = timezone(timedelta(hours=9))
    
    # 日本時間で日付を取得
    now_jst = datetime.now(jst)
    today = now_jst.date()
    yesterday = today - timedelta(days=1)
    day_before_yesterday = today - timedelta(days=2)
    
    # 基本的な日付カテゴリ
    grouped = {
        '本日': [],
        '昨日': [],
        '一昨日': []
    }
    
    # 月別のカテゴリも動的に作成
    monthly_groups = {}
    
    for article in articles:
        try:
            # 記事の公開日時を日本時間に変換
            article_datetime = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
            if article_datetime.tzinfo is None:
                # タイムゾーン情報がない場合はUTCとして扱う
                try:
                    from zoneinfo import ZoneInfo
                    utc = ZoneInfo("UTC")
                except ImportError:
                    from datetime import timezone
                    utc = timezone.utc
                article_datetime = article_datetime.replace(tzinfo=utc)
            
            # 日本時間に変換
            article_datetime_jst = article_datetime.astimezone(jst)
            article_date = article_datetime_jst.date()
            
            # 日付カテゴリ分類（本日・昨日・一昨日）
            if article_date == today:
                grouped['本日'].append(article)
            elif article_date == yesterday:
                grouped['昨日'].append(article)
            elif article_date == day_before_yesterday:
                grouped['一昨日'].append(article)
            
            # 月別分類（全ての記事を月別にも分類）
            month_key = article_date.strftime('%Y-%m')
            if month_key not in monthly_groups:
                monthly_groups[month_key] = []
            monthly_groups[month_key].append(article)
                
        except Exception as e:
            logger.warning(f"日付解析エラー: {article.get('title', 'Unknown')} - {e}")
            # エラーの場合は本日に分類
            grouped['本日'].append(article)
    
    # 月別グループを統合（新しい月から順番）
    for month_key in sorted(monthly_groups.keys(), reverse=True):
        grouped[month_key] = monthly_groups[month_key]
    
    # 各日付内で公開時間順にソート（新しい順）
    for date_key in grouped:
        grouped[date_key].sort(
            key=lambda x: x['published'],
            reverse=True
        )
    
    return grouped

def collect_all_feeds(config: Dict[str, Any], category_keywords: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """全フィードの収集（蓄積型）"""
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
    
    # 新規記事と既存記事をマージ（重複排除）
    all_articles = merge_articles(new_articles, existing_articles)
    
    # 日付別に分類
    articles_by_date = group_articles_by_date(all_articles)
    
    logger.info(f"新規記事: {len(new_articles)}件")
    logger.info(f"マージ後総記事数: {len(all_articles)}件")
    return articles_by_date

def main():
    """メイン処理"""
    try:
        # ロギング設定
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        config = load_config()
        category_keywords = load_category_keywords()
        
        articles_by_date = collect_all_feeds(config, category_keywords)
        save_data(articles_by_date)
        
        logger.info("RSS収集処理が正常に完了しました")
        
    except KeyboardInterrupt:
        logger.info("処理が中断されました")
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        import sys
        sys.exit(1)
