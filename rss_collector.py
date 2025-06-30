#!/usr/bin/env python3
"""
RSS Feed Collector
個人用情報収集サイト向けのRSSフィード収集スクリプト
"""

import json
import feedparser
import requests
from datetime import datetime, timedelta
from pathlib import Path
import sys
import time
from typing import Dict, List, Any
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RSSCollector:
    def __init__(self, config_file: str = "rss_config.json"):
        """RSS収集クラスの初期化"""
        self.config_file = config_file
        self.config = self.load_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def load_config(self) -> Dict[str, Any]:
        """設定ファイルの読み込み"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"設定ファイル {self.config_file} が見つかりません")
            sys.exit(1)
        except json.JSONDecodeError:
            logger.error(f"設定ファイル {self.config_file} の形式が正しくありません")
            sys.exit(1)
    
    def fetch_rss_feed(self, feed_url: str, site_name: str) -> List[Dict[str, Any]]:
        """個別RSSフィードの取得と解析"""
        try:
            logger.info(f"取得開始: {site_name}")
            
            # フィード取得
            response = self.session.get(feed_url, timeout=30)
            response.raise_for_status()
            
            # フィード解析
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"RSS解析警告: {site_name} - {feed.bozo_exception}")
            
            articles = []
            for entry in feed.entries:
                # 記事データの標準化
                article = self.normalize_article(entry, site_name)
                if article and self.is_recent_article(article['published']):
                    articles.append(article)
            
            logger.info(f"取得完了: {site_name} - {len(articles)}件")
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ネットワークエラー ({site_name}): {e}")
            return []
        except Exception as e:
            logger.error(f"予期しないエラー ({site_name}): {e}")
            return []
    
    def normalize_article(self, entry: Any, site_name: str) -> Dict[str, Any]:
        """記事データの正規化"""
        try:
            # タイトル取得
            title = getattr(entry, 'title', '').strip()
            if not title:
                return None
            
            # URL取得
            url = getattr(entry, 'link', '').strip()
            if not url:
                return None
            
            # 公開日時取得
            published = self.parse_date(entry)
            if not published:
                return None
            
            # 概要取得
            description = ''
            if hasattr(entry, 'summary'):
                description = entry.summary
            elif hasattr(entry, 'description'):
                description = entry.description
            
            # HTML タグを除去
            if description:
                import re
                description = re.sub(r'<[^>]+>', '', description).strip()
                # 長すぎる場合は切り詰め
                if len(description) > 200:
                    description = description[:200] + '...'
            
            return {
                'title': title,
                'url': url,
                'site': site_name,
                'published': published.isoformat(),
                'description': description,
                'category': self.get_site_category(site_name)
            }
            
        except Exception as e:
            logger.error(f"記事正規化エラー ({site_name}): {e}")
            return None
    
    def parse_date(self, entry: Any) -> datetime:
        """日付の解析"""
        # 複数の日付フィールドを試行
        date_fields = ['published_parsed', 'updated_parsed']
        
        for field in date_fields:
            if hasattr(entry, field):
                parsed_time = getattr(entry, field)
                if parsed_time:
                    try:
                        return datetime(*parsed_time[:6])
                    except (TypeError, ValueError):
                        continue
        
        # 文字列形式の日付も試行
        string_fields = ['published', 'updated']
        for field in string_fields:
            if hasattr(entry, field):
                date_str = getattr(entry, field)
                if date_str:
                    try:
                        # feedparserの日付解析を使用
                        import email.utils
                        timestamp = email.utils.parsedate_to_datetime(date_str)
                        return timestamp.replace(tzinfo=None)
                    except (TypeError, ValueError):
                        continue
        
        return None
    
    def is_recent_article(self, published_str: str, days: int = 3) -> bool:
        """指定日数以内の記事かどうか判定"""
        try:
            published = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
            published = published.replace(tzinfo=None)  # タイムゾーン情報を削除
            
            cutoff_date = datetime.now() - timedelta(days=days)
            return published >= cutoff_date
        except Exception:
            return True  # 日付が不明な場合は含める
    
    def get_site_category(self, site_name: str) -> str:
        """サイト名からカテゴリを取得"""
        for feed in self.config['rss_feeds']:
            if feed['name'] == site_name:
                return feed['category']
        return 'その他'
    
    def collect_all_feeds(self) -> Dict[str, List[Dict[str, Any]]]:
        """全フィードの収集"""
        logger.info("RSS収集を開始します")
        
        all_articles = []
        enabled_feeds = [feed for feed in self.config['rss_feeds'] if feed['enabled']]
        
        for i, feed in enumerate(enabled_feeds):
            # リクエスト間隔を空ける（サーバー負荷軽減）
            if i > 0:
                time.sleep(2)
            
            articles = self.fetch_rss_feed(feed['url'], feed['name'])
            all_articles.extend(articles)
        
        # 日付別に分類
        articles_by_date = self.group_articles_by_date(all_articles)
        
        logger.info(f"収集完了 - 合計 {len(all_articles)} 件の記事")
        return articles_by_date
    
    def group_articles_by_date(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """記事を日付別にグループ化"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        day_before_yesterday = today - timedelta(days=2)
        
        grouped = {
            '本日': [],
            '昨日': [],
            '一昨日': []
        }
        
        for article in articles:
            try:
                article_date = datetime.fromisoformat(article['published']).date()
                
                if article_date == today:
                    grouped['本日'].append(article)
                elif article_date == yesterday:
                    grouped['昨日'].append(article)
                elif article_date == day_before_yesterday:
                    grouped['一昨日'].append(article)
                    
            except Exception as e:
                logger.warning(f"日付解析エラー: {article.get('title', 'Unknown')} - {e}")
                # エラーの場合は本日に分類
                grouped['本日'].append(article)
        
        # 各日付内で公開時間順にソート（新しい順）
        for date_key in grouped:
            grouped[date_key].sort(
                key=lambda x: x['published'],
                reverse=True
            )
        
        return grouped
    
    def save_data(self, articles_by_date: Dict[str, List[Dict[str, Any]]]) -> None:
        """データの保存"""
        # dataディレクトリの作成
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        # 現在時刻を記録
        timestamp = datetime.now().isoformat()
        
        # メインデータファイル
        output_data = {
            'last_updated': timestamp,
            'total_articles': sum(len(articles) for articles in articles_by_date.values()),
            'articles_by_date': articles_by_date
        }
        
        output_file = data_dir / 'articles.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"データ保存完了: {output_file}")
        
        # 統計情報を表示
        for date_key, articles in articles_by_date.items():
            logger.info(f"{date_key}: {len(articles)}件")

def main():
    """メイン処理"""
    try:
        collector = RSSCollector()
        articles_by_date = collector.collect_all_feeds()
        collector.save_data(articles_by_date)
        logger.info("RSS収集処理が正常に完了しました")
        
    except KeyboardInterrupt:
        logger.info("処理が中断されました")
        sys.exit(1)
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()