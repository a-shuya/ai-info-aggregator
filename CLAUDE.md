# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

このプロジェクトは個人用の情報収集サイトで、複数のWebサイトのRSSフィードから最新記事を自動収集し、日付別に整理して表示するWebアプリケーションです。技術記事やビジネス記事を一箇所で閲覧できるようにすることが目的です。

## 主要なコマンド

### 開発環境
```bash
# 依存関係のインストール
npm install
pip install -r requirements.txt

# 開発サーバーの起動
npm run dev

# 本番ビルド
npm run build

# ビルド結果のプレビュー
npm run preview

# RSSデータの手動収集
python rss_collector.py
```

### データ収集の実行
```bash
# RSS収集スクリプトの実行（public/data/ にタグ別JSON・stats.json・search-index.jsonl が生成される）
python rss_collector.py
```

## アーキテクチャ

### データ収集システム (Python)
- **rss_collector.py**: エントリーポイント（実体は `backend/` パッケージ）
  - `backend/main.py`: オーケストレーション（収集→マージ→保存）
  - `backend/fetcher.py`: RSS取得、`backend/parser.py`: 記事正規化、`backend/storage.py`: 保存・重複排除
- **rss_config.json**: 収集対象のRSSフィード設定 + `retention_days`（保持日数）
- **GitHub Actions**: 10分毎の自動データ更新（.github/workflows/rss-collector.yml）
- **public/data/tags/**: サイト別に分割されたデータファイルの保存先
  - 各サイト（タグ）ごとに `{site, last_updated, total_articles, articles:[新着順フラット配列]}` で保存
  - 例: `日経ビジネス.json`、`Business Insider(ビジネス).json`
  - `public/` 配下なので Astro がビルド時に読め、`/data/...` として実行時 fetch も可能
- **public/data/stats.json**: 軽量な全体統計（最終更新・総件数・サイト別件数・本日/昨日/一昨日件数）
- **public/data/search-index.jsonl**: 全履歴の軽量検索インデックス（title/url/site/published のみ、1行1記事）

### フロントエンド (Astro)
- **Astro**: 静的サイト生成フレームワーク
- **src/pages/index.astro**: 記事一覧表示ページ（メイン画面）
  - 3列固定グリッドレイアウト（PC）、1列（モバイル）
  - 新着順ソート機能（全期間・全タブ対応）
  - 元サイトリンク表示機能
  - **軽量化方針**: 初回HTMLには「直近 `RECENT_DAYS`(=7) 日分」のみインライン。
    過去日付の閲覧・全期間検索は `/data/search-index.jsonl` を**初回のみ lazy fetch**して処理（記事カードはJSで生成）
- **src/pages/home.astro**: 市況・天気ダッシュボード
  - 株価・為替情報（Yahoo Finance API）
  - 東京天気予報（気象庁API）
- **src/layouts/Layout.astro**: 基本レイアウト（記事カードは index.astro 内のJSで生成。専用コンポーネントは無し）

### タグ管理システム
記事データは各サイト（タグ）ごとに分割保存されます：

**現在のタグ一覧（20サイト）:**
- 日経ビジネス
- Business Insider(ビジネス/テック/サイエンス/スタートアップ)
- 日経xTECH(IT)
- ITmedia(AI+)
- はてなブックマーク (IT/AI)
- Zenn(機械学習/AI/生成AI/ディープラーニング/LLM/NLP/Python/Google Cloud)
- Cloud Blog/Cloud Blog JA
- G-gen

**新しいタグの追加方法:**
1. `rss_config.json`に新しいRSSフィードを追加
2. RSS収集実行時に自動的に新しいタグファイルが作成される
3. フロントエンドは自動的に新しいタグを認識・表示

### 天気予報API
市況・天気ページでは気象庁APIを使用：
- **URL**: `https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json`
- **特徴**: APIキー不要、日本時間（JST）ネイティブ、東京都の公式天気データ
- **フォールバック**: API取得失敗時はダミーデータを表示

### デプロイ・ホスティング
- **Vercel**: 自動デプロイ（GitHubへのプッシュ時）
- **GitHub Actions**: 10分毎の自動RSS収集（cron `*/10 * * * *`）
  - タグ別JSON・`stats.json`・`search-index.jsonl`（`public/data/*`）の更新
  - 自動コミット・プッシュでVercel連携

## 主要機能

### 📰 記事一覧機能
- **レイアウト**: 3列固定グリッド（PC）、1列（モバイル・タブレット）
- **ソート**: 新着順表示（全期間・全タブ対応）
- **フィルタ**: サイト別タブ切り替え（20サイト対応）
- **期間選択**: 本日・昨日・一昨日・月別表示
- **元サイトリンク**: 各タブ選択時に右上表示

### 📊 市況・天気ダッシュボード
- **株価情報**: 日経平均・ドル円・S&P500の前日終値と変動
- **天気予報**: 東京3日間予報（3時間ごと、天気記号付き）
- **データ取得**: Yahoo Finance API、気象庁API使用

### 🏷️ タグ管理システム
- **分割保存**: 各サイト別にJSONファイル管理
- **自動拡張**: 新サイト追加時の自動タグファイル作成
- **重複排除**: URL基準での記事重複チェック

### 🎨 UI/UX機能
- **ホバー効果**: 記事カードの立体的な動作
- **ファビコン表示**: 各記事のサイトアイコン
- **レスポンシブ**: PC/モバイル最適化
- **ナビゲーション**: 記事一覧 ↔ 市況・天気の切り替え

## データフロー

1. GitHub ActionsがPythonスクリプトを定期実行（10分毎）
2. スクリプトがRSSフィードを取得・解析
3. 既存記事とマージ（URL重複排除・保持期間で間引き）し `public/data/`（tags / stats.json / search-index.jsonl）へ保存
4. 変更をGitHubにコミット・プッシュ
5. Vercelが自動的に再ビルド・デプロイ

## 設定ファイル

### rss_config.json
RSSフィードの設定を管理。
- トップレベル `retention_days`: 記事の保持日数（既定 3650 ≒ 全期間保持。間引きはこの値で判定）
- `rss_feeds[]` 各フィードの属性：
  - `name`: サイト名 / `url`: RSS URL / `category`: カテゴリ / `enabled`: 有効・無効

### astro.config.mjs
Astroの設定ファイル。Vercel向けの本番サイトURLを設定。

## 日本語対応

- UIは日本語
- 日付表示は日本語形式
- 記事は「本日」「昨日」「一昨日」で分類
- 日本語フォントを使用（Hiragino Sans, Yu Gothic UI, Meiryo）

## 重要な制約

- 個人利用目的のプロジェクト
- RSSフィードのみを使用（スクレイピング回避）
- サーバー負荷軽減のため2秒間隔でリクエスト
- 記事は `retention_days`（既定3650日≒全期間）保持。初回ページは直近7日のみインラインし、過去・検索は検索インデックスを lazy fetch して軽量化