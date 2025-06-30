# RSS フィード一覧

## 現在利用中のRSSフィード

### ビジネス系（2サイト）

| サイト名 | RSS URL | ステータス |
|----------|---------|-----------|
| Business Insider Japan | `https://www.businessinsider.jp/feed/index.xml` | ✅ 利用中 |
| 日経ビジネス電子版 | `https://business.nikkei.com/rss/sns/nb.rdf` | ✅ 利用中 |

### AI・技術系（1サイト）

| サイト名 | RSS URL | ステータス |
|----------|---------|-----------|
| ITmedia AI+ | `https://rss.itmedia.co.jp/rss/2.0/aiplus.xml` | ✅ 利用中 |

### IT・技術系（2サイト）

| サイト名 | RSS URL | ステータス |
|----------|---------|-----------|
| 日経xTECH（IT） | `https://xtech.nikkei.com/rss/xtech-it.rdf` | ✅ 利用中 |
| はてなブックマーク（IT） | `https://b.hatena.ne.jp/hotentry/it.rss` | ✅ 利用中 |

### 開発系（1サイト）

| サイト名 | RSS URL | ステータス |
|----------|---------|-----------|
| Zenn（トレンド） | `https://zenn.dev/feed` | ✅ 利用中 |

## 未利用フィード（URL要確認）

### クラウド系（2サイト）

| サイト名 | RSS URL | ステータス | 備考 |
|----------|---------|-----------|------|
| Google Cloud Blog（日本語） | `https://cloud.google.com/blog/ja/rss` | ❌ 未使用 | RSS URL要確認 |
| G-gen Tech Blog | `https://blog.g-gen.co.jp/feed/` | ❌ 未使用 | RSS URL要確認 |

## RSS収集統計

- **利用中フィード数**: 6サイト
- **未使用フィード数**: 2サイト
- **最新収集記事数**: 109件
  - 本日: 47件
  - 昨日: 50件
  - 一昨日: 10件

## 設定ファイル

RSS設定は `rss_config.json` で管理されています。

```json
{
  "rss_feeds": [
    {
      "name": "サイト名",
      "url": "RSS URL",
      "category": "カテゴリ",
      "enabled": true/false,
      "note": "備考（オプション）"
    }
  ]
}
```

## 新規RSSフィード追加手順

1. `rss_config.json` に新しいフィード情報を追加
2. `enabled: true` に設定
3. GitHub Actions で自動収集が開始される
4. サイトのタブが自動的に追加される

## 法的確認済み

すべての利用中RSSフィードは以下を確認済み：
- ✅ 公式RSS提供
- ✅ robots.txt準拠
- ✅ 利用規約違反なし