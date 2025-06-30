# AI Info Aggregator

個人用情報収集サイト - 最新のビジネス・技術記事を一箇所で閲覧

## 概要

複数のWebサイトの公式RSSフィードから最新記事を自動収集し、日付別に整理して表示するWebアプリケーションです。

## 特徴

- 📡 **RSS ベース**: 公式RSSフィードを使用した安全な情報収集
- 📅 **日付別表示**: 本日・昨日・一昨日の記事を分類表示
- ⚡ **高速表示**: Astro による静的サイト生成で高速ページ読み込み
- 📱 **レスポンシブ**: PC・タブレット・スマートフォン対応
- 🤖 **自動更新**: GitHub Actions による1時間毎の自動データ更新

## 収集対象サイト

- Business Insider Japan
- 日経ビジネス電子版
- ITmedia AI+
- 日経xTECH（IT）
- はてなブックマーク（IT）
- Zenn（トレンド）

## 技術スタック

### バックエンド (データ収集)
- Python 3.11+
- feedparser (RSS解析)
- GitHub Actions (定期実行)

### フロントエンド (表示)
- Astro (静的サイト生成)
- Tailwind CSS (スタイリング)
- TypeScript

### ホスティング
- Vercel / Netlify (予定)

## ローカル開発

### 必要な環境
- Python 3.11+
- Node.js 18+

### セットアップ

1. リポジトリのクローン
```bash
git clone <repository-url>
cd ai-info-aggregator
```

2. Python 依存関係のインストール
```bash
pip install -r requirements.txt
```

3. RSS データの収集
```bash
python rss_collector.py
```

4. Node.js 依存関係のインストール
```bash
npm install
```

5. 開発サーバーの起動
```bash
npm run dev
```

## デプロイ

### GitHub Actions
- `.github/workflows/rss-collector.yml` が1時間毎にRSSデータを更新
- データ更新時に自動的にVercelへデプロイ

### Vercel設定
1. GitHub リポジトリを Vercel に接続
2. Build Command: `npm run build`
3. Output Directory: `dist`
4. 自動デプロイを有効化

## ライセンス

このプロジェクトは個人利用目的で作成されています。収集される記事の著作権は各配信元に帰属します。

## 免責事項

- このサイトは各サイトの公式RSSフィードを利用して情報を収集しています
- 記事の内容や正確性については各配信元にお問い合わせください
- 個人利用の範囲での使用に限定されます