# Developer Information Collection

## Project Overview

ゲーム開発者コミュニティ（Discord）向けに、ゲーム開発関連の情報を
Webサイトからスクレイピングして収集し、Discord投稿用にまとめるツール。

### 収集カテゴリ

| カテゴリ | 内容 | 出力先 |
|----------|------|--------|
| イベント | 関東圏・関西圏のゲーム開発イベントスケジュール | `output/events/` |
| フリーアセット | 無料素材のまとめ記事（Qiita, Zenn, Note.com） | `output/free-assets/` |
| 学習リソース | Unity中心のゲーム開発学習記事 | `output/learning-resources/` |
| 周辺機器 | ゲーム開発周辺機器のレビュー・おすすめ記事 | `output/peripherals/` |

このProjectは **Discordへの公開前段階** として、情報の収集・整理を担当する。

## System Architecture

```
[Web Sources]  →  [Scraper (Python)]  →  [Markdown Summary]  →  [Discord投稿]

イベント:                                  月刊カレンダー
  connpass (Playwright)                    (地域別)
  Peatix (Playwright)
  kokuchpro (requests+BS4)

記事:                                      いいね数ソート
  Qiita API v2 (requests)                  リンク集
  Zenn API (requests)
  Note.com API (requests)
                                           (このProjectの範囲)    (別途実装)
```

## Usage

```bash
# イベント収集（デフォルト: 来月）
python src/main.py                           # 来月のイベントを取得
python src/main.py --month 202603            # 2026年3月のイベントを取得
python src/main.py --connpass-only           # connpassのみ
python src/main.py --peatix-only             # Peatixのみ
python src/main.py --kokuchpro-only          # こくちーずプロのみ

# 記事収集
python src/main.py --articles                         # 全記事カテゴリ
python src/main.py --articles --category free-assets  # フリーアセット記事のみ
python src/main.py --articles --category learning-resources  # 学習リソースのみ
python src/main.py --articles --category peripherals  # 周辺機器のみ
python src/main.py --articles --qiita-only            # Qiitaのみ
python src/main.py --articles --zenn-only             # Zennのみ
python src/main.py --articles --note-only             # Note.comのみ

# 全収集（イベント + 全記事カテゴリ）
python src/main.py --all
```

## Discord発信フォーマット

### チャンネル構成

- `#📅｜関東イベント` - 関東圏のゲーム開発イベント
- `#📅｜関西イベント` - 関西圏のゲーム開発イベント

### イベント（月刊カレンダー形式）

```
📅 **2026年3月 関東ゲーム開発イベント**

**3/5(木)** Unity Meetup Tokyo #42
└ 19:00-21:00 ｜ 渋谷 ｜ 無料
└ https://connpass.com/event/xxxxx

---
最終更新: 2026/3/1
```

### 記事（いいね数ソートのリンク集）

```
# ゲーム用フリーアセットまとめ記事 (2026年3月収集)

**1.** [Unity初心者向け無料アセットまとめ2026](https://qiita.com/xxx)
└ @author_name ｜ 2026/03/05 ｜ 42 likes ｜ Qiita
└ タグ: Unity, ゲーム開発, フリー素材

---
最終更新: 2026/03/01 10:30
```

### 地域分類

| 地域 | 対象エリア |
|------|-----------|
| 関東圏 | 東京、神奈川、千葉、埼玉 等 |
| 関西圏 | 大阪、京都、兵庫、奈良 等 |

## Scraping Target Sites

### イベントソース

| サイト | 取得方法 | 備考 |
|--------|----------|------|
| connpass | Playwright | Web検索ページをスクレイピング |
| Peatix | Playwright | SPA対応、User-Agent + locale=ja-JP必須 |
| こくちーずプロ | requests + BS4 | 「ゲーム業界」特集ページから取得 |

### 記事ソース

| サイト | 取得方法 | 備考 |
|--------|----------|------|
| Qiita | API v2 (requests) | 認証不要、レートリミット60回/時 |
| Zenn | 内部API (requests) | `/api/articles` エンドポイント |
| Note.com | 内部API (requests) | `/api/v3/searches` エンドポイント |

## Tech Stack

- **Language**: Python 3.x
- **イベント**: `Playwright`（connpass, Peatix） + `requests`+`BeautifulSoup`（kokuchpro）
- **記事**: `requests`（Qiita API v2, Zenn API, Note.com API）
- **共通**: `filters.py`（キーワードフィルタ）、`http_utils.py`（リトライ付きHTTP）
- **Output**: Markdown files（月別・カテゴリ別）
- **Discord連携**: Webhook or Bot（別途実装）

## Project Structure

```
developer-information-collection/
├── CLAUDE.md                 # プロジェクト設定・ルール
├── requirements.txt          # Python依存パッケージ
├── config/
│   └── sites.json            # スクレイピング設定（検索キーワード、日付範囲等）
├── src/
│   ├── main.py               # メインスクリプト（CLI）
│   ├── filters.py            # 共通キーワードフィルタリング
│   ├── http_utils.py         # 共通HTTPユーティリティ（リトライ、UA）
│   ├── scraper_connpass.py   # connpassスクレイパー（Playwright）
│   ├── scraper_peatix.py     # Peatixスクレイパー（Playwright）
│   ├── scraper_kokuchpro.py  # こくちーずプロスクレイパー（requests + BS4）
│   ├── scraper_qiita.py      # Qiita記事スクレイパー（API v2）
│   ├── scraper_zenn.py       # Zenn記事スクレイパー（内部API）
│   ├── scraper_note.py       # Note.com記事スクレイパー（内部API）
│   ├── classifier.py         # 地域分類（関東/関西）
│   ├── formatter.py          # イベント用Markdown整形（カレンダー形式）
│   └── article_formatter.py  # 記事用Markdown整形（リンク集形式）
└── output/
    ├── events/               # イベント（月別・地域別）
    ├── free-assets/          # フリーアセットまとめ記事
    ├── learning-resources/   # 学習リソース記事
    └── peripherals/          # 周辺機器レビュー記事
```

## Config Structure (sites.json)

```json
{
  "connpass": { ... },         // connpass検索設定
  "peatix": { ... },           // Peatix検索設定
  "kokuchpro": { ... },        // こくちーずプロ設定
  "filtering": {
    "events": {
      "relevance_keywords": [...],  // イベント関連性キーワード
      "exclude_keywords": [...]     // イベント除外キーワード
    }
  },
  "articles": {
    "free-assets": {
      "qiita": { "queries": [...] },
      "zenn": { "queries": [...] },
      "note": { "queries": [...] },
      "relevance_keywords": [...],
      "exclude_keywords": [...]
    },
    "learning-resources": { ... },
    "peripherals": { ... }
  },
  "regions": { ... }
}
```

## Workflow

### イベント収集フロー
1. `config/sites.json` から検索条件を読み込む
2. connpass / Peatix / kokuchpro からイベントを取得
3. 全ソース横断でURL重複を排除
4. `classifier.py` で地域分類（住所から関東/関西を判定）
5. `formatter.py` で月刊カレンダー形式のMarkdownに整形
6. `output/events/` に月別・地域別で保存

### 記事収集フロー
1. `config/sites.json` から検索クエリ・フィルタ設定を読み込む
2. Qiita API / Zenn API / Note.com API から記事を取得
3. URL重複排除 + キーワードフィルタリング
4. `article_formatter.py` でいいね数ソートのリンク集Markdownに整形
5. `output/{category}/` にカテゴリ別で保存

## CI/CD (GitHub Actions)

### 定期バッチ: イベント収集

- **ファイル**: `.github/workflows/weekly-events.yml`
- **スケジュール**: 毎週日曜 08:00 JST（cron: `0 23 * * 6` UTC）
- **収集対象**: イベントのみ（`python src/main.py --events`）
- **動作**: 収集結果を `output/events/` にコミット＆プッシュ
- **手動実行**: GitHub の Actions タブから `workflow_dispatch` で随時実行可能

## Scraping Rules

- robots.txt を尊重し、過度なリクエストは行わない
- リクエスト間隔は最低1秒空ける
- 取得データはコミュニティ内での情報共有目的に限定する
- 引用元URLを必ず記載する
