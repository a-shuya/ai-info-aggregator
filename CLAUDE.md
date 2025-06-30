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
# RSS収集スクリプトの実行（dataディレクトリにarticles.jsonが生成される）
python rss_collector.py
```

## アーキテクチャ

### データ収集システム (Python)
- **rss_collector.py**: メインの収集スクリプト
- **rss_config.json**: 収集対象のRSSフィード設定
- **GitHub Actions**: 1時間毎の自動データ更新（.github/workflows/rss-collector.yml）
- **data/tags/**: サイト別に分割されたデータファイルの保存先
  - 各サイト（タグ）ごとに個別のJSONファイルに分割保存
  - 例: `日経ビジネス.json`、`Business Insider(ビジネス).json`
- **data/articles_summary.json**: 全体統計情報（互換性のため）

### フロントエンド (Astro)
- **Astro**: 静的サイト生成フレームワーク
- **src/pages/index.astro**: 記事一覧表示ページ
- **src/pages/home.astro**: ホームページ（ダッシュボード）
- **src/layouts/Layout.astro**: 基本レイアウト
- **src/components/ArticleCard.astro**: 記事カードコンポーネント

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

### APIキー設定
ホームページの天気予報機能を使用するには、OpenWeatherMapの無料APIキーが必要です：
1. https://openweathermap.org/api でアカウント作成
2. 無料のCurrent Weather Data APIキーを取得
3. `src/pages/home.astro`の`API_KEY`変数を実際のキーに置き換え

### デプロイ・ホスティング
- **Vercel**: 自動デプロイ（GitHubへのプッシュ時）
- **GitHub Actions**: 定期的なデータ更新とコミット

## データフロー

1. GitHub ActionsがPythonスクリプトを定期実行
2. スクリプトがRSSフィードを取得・解析
3. 記事データをdata/articles.jsonに保存
4. 変更をGitHubにコミット・プッシュ
5. Vercelが自動的に再ビルド・デプロイ

## 設定ファイル

### rss_config.json
RSSフィードの設定を管理。各フィードには以下の属性：
- `name`: サイト名
- `url`: RSS URL
- `category`: カテゴリ
- `enabled`: 有効/無効の切り替え

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
- 最新3日分の記事のみ保持