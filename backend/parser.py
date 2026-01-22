import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def parse_date(entry: Any) -> Optional[datetime]:
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

def extract_image_url(entry: Any) -> str:
    """RSS エントリから画像URLを抽出"""
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

def extract_rss_category(entry: Any) -> str:
    """RSSエントリからカテゴリを抽出"""
    try:
        # Business Insiderのcategoryフィールドから直接取得
        if hasattr(entry, 'tags') and entry.tags:
            # 最初のタグのtermを使用（Business Insiderの場合）
            return entry.tags[0].term if hasattr(entry.tags[0], 'term') else ''
            
        return ''
    except Exception as e:
        logger.warning(f"RSSカテゴリ抽出エラー: {e}")
        return ''

def normalize_article(entry: Any, site_name: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
        published = parse_date(entry)
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
            description = re.sub(r'<[^>]+>', '', description).strip()
            # 長すぎる場合は切り詰め
            if len(description) > 200:
                description = description[:200] + '...'
        
        # 画像URL取得
        image_url = extract_image_url(entry)
        
        # RSS カテゴリ取得（Business Insider用）
        rss_category = extract_rss_category(entry)
        
        # サイト構成からカテゴリを取得
        site_category = 'その他'
        for feed in config.get('rss_feeds', []):
            if feed['name'] == site_name:
                site_category = feed['category']
                break

        return {
            'title': title,
            'url': url,
            'site': site_name,
            'published': published.isoformat() + 'Z',  # Add UTC timezone indicator
            'description': description,
            'category': site_category,
            'rss_category': rss_category,  # RSS元カテゴリを保存
            'image_url': image_url
        }
        
    except Exception as e:
        logger.error(f"記事正規化エラー ({site_name}): {e}")
        return None

def is_recent_article(published_str: str, days: int = 365) -> bool:
    """指定日数以内の記事かどうか判定（デフォルト1年間）"""
    try:
        published = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
        published = published.replace(tzinfo=None)  # タイムゾーン情報を削除
        
        cutoff_date = datetime.now() - timedelta(days=days)
        return published >= cutoff_date
    except Exception:
        return True  # 日付が不明な場合は含める
