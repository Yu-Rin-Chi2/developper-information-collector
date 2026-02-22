# Developer Information Collection

## Project Overview

ゲーム開発者コミュニティ（Discord）向けに、関東圏・関西圏のゲーム開発関連イベント情報を
Webサイトからスクレイピングして収集し、月刊カレンダー形式でまとめるツール。

このProjectは **Discordへの公開前段階** として、情報の収集・整理を担当する。

## System Architecture

```
[Web Sources]  →  [Scraper (Python)]  →  [Markdown Summary]  →  [Discord投稿]
connpass等          収集・整形              月刊カレンダー         Webhook/Bot
                                           (このProjectの範囲)    (別途実装)
```

## Discord発信フォーマット

### チャンネル構成

- `#📅｜関東イベント` - 関東圏のゲーム開発イベント
- `#📅｜関西イベント` - 関西圏のゲーム開発イベント

### 月刊カレンダー形式

月初に1回、その月のイベント一覧をまとめて投稿（ピン留め）。

```
📅 **2026年3月 関東ゲーム開発イベント**

**3/5(木)** Unity Meetup Tokyo #42
└ 19:00-21:00 ｜ 渋谷 ｜ 無料
└ https://connpass.com/event/xxxxx

**3/12(木)** Indie Game Dev 勉強会
└ 18:30-20:30 ｜ 秋葉原 ｜ ¥500
└ https://connpass.com/event/xxxxx

**3/20(土)** GDC 2026 報告会
└ 14:00-17:00 ｜ 渋谷 ｜ ¥1000
└ https://connpass.com/event/xxxxx

---
⚠️ 最終更新: 2026/3/1
```

### イベント情報の項目（基本情報）

| 項目 | 説明 |
|------|------|
| イベント名 | イベントのタイトル |
| 日付・曜日 | 開催日と曜日 |
| 時間 | 開始時間〜終了時間 |
| 場所 | 開催エリア（渋谷、梅田 等） |
| 参加費 | 無料 or 金額 |
| リンク | 申込・詳細ページのURL |

### 地域分類

| 地域 | 対象エリア |
|------|-----------|
| 関東圏 | 東京、神奈川、千葉、埼玉 等 |
| 関西圏 | 大阪、京都、兵庫、奈良 等 |

## Scraping Target Sites

### 1. connpass（API v2使用）

- **API**: `https://connpass.com/api/v2/events/`
- **取得方法**: `requests`（REST API、JSONレスポンス）
- **認証**: `X-API-Key` ヘッダー（APIキー必要、環境変数 `CONNPASS_API_KEY` で設定）
- **レートリミット**: 1秒に1リクエスト
- **主要パラメータ**: `keyword`, `ym`(年月), `prefecture`(都道府県), `order`, `count`, `start`
- **取得可能データ**: title, started_at, ended_at, address, place, url, accepted/limit
- **備考**: `prefecture` パラメータで都道府県フィルタが直接可能

### 2. Peatix

- **URL**: `https://peatix.com/search?lang=ja&q=ゲーム`
- **レンダリング**: JavaScript SPA（動的レンダリング）
- **取得方法**: `Playwright`（ヘッドレスブラウザ）が必要
- **取得可能データ**: イベント名、日付・曜日・開始時間、会場名・住所、主催者、リンク
- **ページネーション**: 「次」ボタンによるページ送り
- **内部API**: `https://peatix.com/search/events?q=...&country=JP&l.ll=LAT,LNG&p=PAGE&size=20`
  （ただしHTMLを返すため、直接JSON取得は不可）
- **DOM構造**:
  - 各イベント: `listitem` > `link` 内に全情報
  - 日付: `<time>` タグ（例: "3月 13"）
  - 時間: `<time>` タグ（例: "金曜日 18:00"）
  - 会場: テキストノード（"会場: ○○ 住所"）
  - タイトル: `<h3>` タグ
  - 主催: テキストノード（"主催: ○○"）
- **備考**: 「ゲーム」検索はボードゲーム・ビジネスゲーム等も含むため、
  ゲーム開発関連のフィルタリング（キーワード除外等）が必要

## Tech Stack

- **Language**: Python 3.x
- **connpass**: `requests`（公式API v2、JSONレスポンス）
- **Peatix**: `Playwright`（SPA対応、ヘッドレスブラウザ、User-Agent + locale=ja-JP必須）
- **Output**: Markdown files（月別・地域別）
- **Discord連携**: Webhook or Bot（別途実装）

## Project Structure

```
developer-information-collection/
├── CLAUDE.md              # プロジェクト設定・ルール
├── requirements.txt       # Python依存パッケージ
├── src/
│   ├── scraper_connpass.py   # connpassスクレイパー
│   ├── scraper_peatix.py     # Peatixスクレイパー（Playwright）
│   ├── classifier.py         # 地域分類（関東/関西）
│   └── formatter.py          # Markdown整形処理（カレンダー形式）
├── config/
│   └── sites.json         # スクレイピング設定（検索キーワード、日付範囲等）
└── output/
    ├── 2026-03_kanto.md   # 関東イベント（月別）
    └── 2026-03_kansai.md  # 関西イベント（月別）
```

## Workflow

1. `config/sites.json` から検索条件を読み込む
2. `scraper_connpass.py` でconnpassのイベントを取得（requests + BS4）
3. `scraper_peatix.py` でPeatixのイベントを取得（Playwright）
4. `classifier.py` で地域分類（住所から関東/関西を判定）
5. `formatter.py` で月刊カレンダー形式のMarkdownに整形
6. `output/` に月別・地域別で保存
7. （将来）Discord Webhook/Botで自動投稿

## Scraping Rules

- robots.txt を尊重し、過度なリクエストは行わない
- リクエスト間隔は最低1秒空ける
- 取得データはコミュニティ内での情報共有目的に限定する
- 引用元URLを必ず記載する
