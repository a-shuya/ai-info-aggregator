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
        self.category_keywords = self.load_category_keywords()
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
    
    def load_category_keywords(self) -> Dict[str, Any]:
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
            
            # 画像URL取得
            image_url = self.extract_image_url(entry)
            
            return {
                'title': title,
                'url': url,
                'site': site_name,
                'published': published.isoformat() + 'Z',  # Add UTC timezone indicator
                'description': description,
                'category': self.get_site_category(site_name),
                'image_url': image_url
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
    
    def is_recent_article(self, published_str: str, days: int = 365) -> bool:
        """指定日数以内の記事かどうか判定（デフォルト1年間）"""
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
    
    def extract_image_url(self, entry: Any) -> str:
        """RSS エントリから画像URLを抽出"""
        import re
        
        # 複数の方法で画像URLを取得を試行
        image_url = ''
        
        # 1. media:content や enclosure から
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if hasattr(enclosure, 'type') and enclosure.type and 'image' in enclosure.type:
                    if hasattr(enclosure, 'href'):
                        image_url = enclosure.href
                        break
        
        # 2. summary や description から img タグを抽出
        if not image_url:
            content = ''
            if hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description
            
            if content:
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
                if img_match:
                    image_url = img_match.group(1)
        
        # 3. media_content から
        if not image_url and hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if hasattr(media, 'url') and hasattr(media, 'type'):
                    if 'image' in media.type:
                        image_url = media.url
                        break
        
        return image_url
    
    def classify_business_insider_article(self, title: str, description: str) -> str:
        """Business Insider記事のカテゴリ分類"""
        if not self.category_keywords or 'business_insider_categories' not in self.category_keywords:
            return 'ビジネス'  # デフォルトカテゴリ
        
        # タイトルと説明を結合してテキスト解析
        text = f"{title} {description}".lower()
        
        # カテゴリ別スコア計算
        category_scores = {}
        categories = self.category_keywords['business_insider_categories']
        
        for category, config in categories.items():
            score = 0
            for keyword in config['keywords']:
                if keyword.lower() in text:
                    score += 1
            category_scores[category] = score
        
        # 最高スコアのカテゴリを返す（スコアが0の場合はデフォルト）
        if category_scores and max(category_scores.values()) > 0:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        
        return 'ビジネス'  # デフォルトカテゴリ
    
    def load_existing_data(self) -> Dict[str, Dict[str, Any]]:
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
    
    def merge_articles(self, new_articles: List[Dict[str, Any]], existing_articles: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            if url not in added_urls and self.is_recent_article(article.get('published', ''), days=365):
                merged_articles.append(article)
                added_urls.add(url)
        
        return merged_articles
    
    def collect_all_feeds(self) -> Dict[str, List[Dict[str, Any]]]:
        """全フィードの収集（蓄積型）"""
        logger.info("RSS収集を開始します")
        
        # 既存データを読み込み
        existing_articles = self.load_existing_data()
        logger.info(f"既存記事数: {len(existing_articles)}件")
        
        new_articles = []
        enabled_feeds = [feed for feed in self.config['rss_feeds'] if feed['enabled']]
        
        for i, feed in enumerate(enabled_feeds):
            # リクエスト間隔を空ける（サーバー負荷軽減）
            if i > 0:
                time.sleep(2)
            
            articles = self.fetch_rss_feed(feed['url'], feed['name'])
            
            # Business Insiderの記事をカテゴリ別に分類
            if feed['name'] == 'Business Insider Japan':
                categorized_articles = []
                for article in articles:
                    classified_category = self.classify_business_insider_article(
                        article['title'], 
                        article.get('description', '')
                    )
                    
                    # 元の記事をコピーしてカテゴリを更新
                    for target_category in ['ビジネス', 'テック', 'サイエンス', 'スタートアップ']:
                        if classified_category == target_category:
                            categorized_article = article.copy()
                            categorized_article['site'] = f'Business Insider({target_category})'
                            categorized_article['category'] = target_category
                            categorized_articles.append(categorized_article)
                            break
                
                new_articles.extend(categorized_articles)
            else:
                new_articles.extend(articles)
        
        # 新規記事と既存記事をマージ（重複排除）
        all_articles = self.merge_articles(new_articles, existing_articles)
        
        # 日付別に分類
        articles_by_date = self.group_articles_by_date(all_articles)
        
        logger.info(f"新規記事: {len(new_articles)}件")
        logger.info(f"マージ後総記事数: {len(all_articles)}件")
        return articles_by_date
    
    def group_articles_by_date(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
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
    
    def save_data(self, articles_by_date: Dict[str, List[Dict[str, Any]]]) -> None:
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