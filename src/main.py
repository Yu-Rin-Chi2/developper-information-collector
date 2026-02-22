"""ゲーム開発情報収集ツール メインスクリプト

Usage:
    # イベント収集（既存互換）
    python src/main.py                    # 来月のイベントを取得
    python src/main.py --month 202603     # 2026年3月のイベントを取得
    python src/main.py --connpass-only    # connpassのみ
    python src/main.py --peatix-only      # Peatixのみ
    python src/main.py --kokuchpro-only   # こくちーずプロのみ

    # 記事収集
    python src/main.py --articles                         # 全記事カテゴリ
    python src/main.py --articles --category free-assets  # 特定カテゴリ
    python src/main.py --articles --qiita-only            # Qiitaのみ
    python src/main.py --articles --zenn-only             # Zennのみ
    python src/main.py --articles --note-only             # Note.comのみ

    # 全収集
    python src/main.py --all                              # イベント + 全記事
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Windows cp932 文字化け対策
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper_connpass import fetch_and_parse as connpass_fetch
from scraper_peatix import fetch_events as peatix_fetch
from scraper_kokuchpro import fetch_events as kokuchpro_fetch
from scraper_qiita import fetch_articles as qiita_fetch
from scraper_zenn import fetch_articles as zenn_fetch
from scraper_note import fetch_articles as note_fetch
from classifier import classify_events
from formatter import save_calendar
from article_formatter import save_article_list


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "sites.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

ARTICLE_CATEGORIES = ["free-assets", "learning-resources", "peripherals"]


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_target_month(month_str: str | None) -> tuple[int, int]:
    """対象年月を取得する。

    Args:
        month_str: "YYYYMM" 形式の文字列。None の場合は来月

    Returns:
        (year, month) のタプル
    """
    if month_str:
        year = int(month_str[:4])
        month = int(month_str[4:6])
        return year, month

    # デフォルト: 来月
    now = datetime.now()
    if now.month == 12:
        return now.year + 1, 1
    return now.year, now.month + 1


def collect_connpass_events(config: dict, year: int, month: int) -> list[dict]:
    """connpass検索ページからイベントを収集する（Playwright版）。"""
    connpass_config = config.get("connpass", {})
    keywords = connpass_config.get("keywords", ["ゲーム開発"])
    months_ahead = connpass_config.get("months_ahead", 6)
    filtering = config.get("filtering", {}).get("events", {})
    exclude = filtering.get("exclude_keywords", [])
    relevance = filtering.get("relevance_keywords", [])

    # 検索期間: 対象月の1日 〜 months_ahead ヶ月後
    start_from = f"{year}/{month:02d}/01"
    end_date = datetime(year, month, 1) + relativedelta(months=months_ahead)
    start_to = end_date.strftime("%Y/%m/%d")

    all_events = []
    seen_urls = set()
    for keyword in keywords:
        print(f"  connpass: キーワード '{keyword}' で検索中...")
        events = connpass_fetch(keyword, start_from, start_to, exclude, relevance)
        for event in events:
            if event["url"] not in seen_urls:
                seen_urls.add(event["url"])
                all_events.append(event)
        print(f"  → {len(events)} 件取得")

    return all_events


def collect_peatix_events(config: dict) -> list[dict]:
    """Peatixからイベントを収集する（各地域の座標で検索）。"""
    peatix_config = config.get("peatix", {})
    keywords = peatix_config.get("keywords", ["ゲーム開発"])
    filtering = config.get("filtering", {}).get("events", {})
    exclude = filtering.get("exclude_keywords", [])
    relevance = filtering.get("relevance_keywords", [])
    locations = peatix_config.get("locations", {})

    all_events = []
    seen_urls = set()

    for region_key, location in locations.items():
        region_label = config.get("regions", {}).get(region_key, {}).get("label", region_key)
        print(f"  Peatix ({region_label}): キーワード {keywords} で検索中...")
        events = peatix_fetch(keywords, exclude, relevance, location=location)
        new_count = 0
        for event in events:
            if event["url"] not in seen_urls:
                seen_urls.add(event["url"])
                all_events.append(event)
                new_count += 1
        print(f"  → {new_count} 件取得 (重複除外済)")

    return all_events


def collect_kokuchpro_events(config: dict) -> list[dict]:
    """こくちーずプロからイベントを収集する。"""
    kokuchpro_config = config.get("kokuchpro", {})
    base_url = kokuchpro_config.get("base_url", "")
    if not base_url:
        print("警告: kokuchpro の base_url が設定されていません。スキップします。")
        return []

    filtering = config.get("filtering", {}).get("events", {})
    exclude = filtering.get("exclude_keywords", [])
    relevance = filtering.get("relevance_keywords", [])

    print(f"  kokuchpro: {base_url} から取得中...")
    events = kokuchpro_fetch(base_url, exclude, relevance)
    print(f"  → {len(events)} 件取得")

    return events


def collect_articles(config: dict, category: str,
                     qiita_only: bool = False,
                     zenn_only: bool = False,
                     note_only: bool = False) -> list[dict]:
    """指定カテゴリの記事を全ソースから収集する。"""
    articles_config = config.get("articles", {}).get(category, {})
    if not articles_config:
        print(f"警告: カテゴリ '{category}' の設定がありません。スキップします。")
        return []

    label = articles_config.get("label", category)
    exclude = articles_config.get("exclude_keywords", [])
    relevance = articles_config.get("relevance_keywords", [])

    all_articles = []
    seen_urls = set()
    single_source = qiita_only or zenn_only or note_only

    def add_articles(new_articles: list[dict]):
        for article in new_articles:
            url = article.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_articles.append(article)

    # Qiita
    if not single_source or qiita_only:
        qiita_config = articles_config.get("qiita", {})
        queries = qiita_config.get("queries", [])
        if queries:
            print(f"  Qiita ({label}): {len(queries)} クエリで検索中...")
            try:
                articles = qiita_fetch(
                    queries, exclude, relevance,
                    per_page=qiita_config.get("per_page", 20),
                    max_pages=qiita_config.get("max_pages", 2),
                    category=category
                )
                add_articles(articles)
                print(f"  → {len(articles)} 件取得")
            except Exception as e:
                print(f"  警告: Qiita取得失敗: {e}")

    # Zenn
    if not single_source or zenn_only:
        zenn_config = articles_config.get("zenn", {})
        queries = zenn_config.get("queries", [])
        if queries:
            print(f"  Zenn ({label}): {len(queries)} クエリで検索中...")
            try:
                articles = zenn_fetch(
                    queries, exclude, relevance,
                    max_pages=zenn_config.get("max_pages", 2),
                    category=category
                )
                add_articles(articles)
                print(f"  → {len(articles)} 件取得")
            except Exception as e:
                print(f"  警告: Zenn取得失敗: {e}")

    # Note.com
    if not single_source or note_only:
        note_config = articles_config.get("note", {})
        queries = note_config.get("queries", [])
        if queries:
            print(f"  Note.com ({label}): {len(queries)} クエリで検索中...")
            try:
                articles = note_fetch(
                    queries, exclude, relevance,
                    max_pages=note_config.get("max_pages", 2),
                    category=category
                )
                add_articles(articles)
                print(f"  → {len(articles)} 件取得")
            except Exception as e:
                print(f"  警告: Note.com取得失敗: {e}")

    return all_articles


def run_events(config: dict, year: int, month: int, args) -> None:
    """イベント収集を実行する。"""
    print(f"\n{'='*50}")
    print(f"イベント収集")
    print(f"{'='*50}")

    single_source = args.connpass_only or args.peatix_only or args.kokuchpro_only

    all_events = []
    seen_urls = set()

    def add_events(events: list[dict]):
        for event in events:
            url = event.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_events.append(event)

    if not single_source or args.connpass_only:
        try:
            events = collect_connpass_events(config, year, month)
            add_events(events)
        except Exception as e:
            print(f"警告: connpassの取得に失敗しました: {e}")
            print("Playwrightがインストールされているか確認してください:")
            print("  pip install playwright && playwright install chromium")

    if not single_source or args.peatix_only:
        try:
            events = collect_peatix_events(config)
            add_events(events)
        except Exception as e:
            print(f"警告: Peatixの取得に失敗しました: {e}")
            print("Playwrightがインストールされているか確認してください:")
            print("  pip install playwright && playwright install chromium")

    if not single_source or args.kokuchpro_only:
        try:
            events = collect_kokuchpro_events(config)
            add_events(events)
        except Exception as e:
            print(f"警告: kokuchproの取得に失敗しました: {e}")

    print(f"\n合計: {len(all_events)} 件のイベントを取得")

    # 地域分類
    classified = classify_events(all_events)

    for region in ["kanto", "kansai"]:
        events = classified[region]
        print(f"\n{region}: {len(events)} 件")

        events_dir = os.path.join(OUTPUT_DIR, "events")
        filepath = save_calendar(events, region, year, month, events_dir)
        print(f"  → {filepath}")

    other_count = len(classified.get("other", []))
    if other_count > 0:
        print(f"\nその他（地域不明/オンライン）: {other_count} 件")


def run_articles(config: dict, year: int, month: int, args) -> None:
    """記事収集を実行する。"""
    categories = [args.category] if args.category else ARTICLE_CATEGORIES

    for category in categories:
        print(f"\n{'='*50}")
        print(f"記事収集: {category}")
        print(f"{'='*50}")

        articles = collect_articles(
            config, category,
            qiita_only=args.qiita_only,
            zenn_only=args.zenn_only,
            note_only=args.note_only
        )
        print(f"\n{category}: {len(articles)} 件の記事を取得")

        if articles:
            filepath = save_article_list(articles, category, year, month, OUTPUT_DIR)
            print(f"  → {filepath}")


def main():
    parser = argparse.ArgumentParser(description="ゲーム開発情報収集ツール")
    parser.add_argument("--month", type=str, default=None,
                        help="対象年月 (YYYYMM形式, デフォルト: 来月)")

    # モード選択
    mode_group = parser.add_argument_group("収集モード")
    mode_group.add_argument("--events", action="store_true",
                            help="イベント情報のみ取得")
    mode_group.add_argument("--articles", action="store_true",
                            help="記事情報のみ取得")
    mode_group.add_argument("--all", action="store_true",
                            help="イベント + 記事 全て取得")

    # イベントソース指定
    event_group = parser.add_argument_group("イベントソース指定")
    event_group.add_argument("--connpass-only", action="store_true",
                             help="connpassのみ取得")
    event_group.add_argument("--peatix-only", action="store_true",
                             help="Peatixのみ取得")
    event_group.add_argument("--kokuchpro-only", action="store_true",
                             help="こくちーずプロのみ取得")

    # 記事オプション
    article_group = parser.add_argument_group("記事オプション")
    article_group.add_argument("--category", type=str, default=None,
                               choices=ARTICLE_CATEGORIES,
                               help="記事カテゴリを指定（--articlesと併用）")
    article_group.add_argument("--qiita-only", action="store_true",
                               help="Qiitaのみ取得（記事モード）")
    article_group.add_argument("--zenn-only", action="store_true",
                               help="Zennのみ取得（記事モード）")
    article_group.add_argument("--note-only", action="store_true",
                               help="Note.comのみ取得（記事モード）")

    args = parser.parse_args()

    # 対象月
    year, month = get_target_month(args.month)
    print(f"対象: {year}年{month}月")

    # 設定読み込み
    config = load_config()

    # モード判定
    do_events = args.events or args.all or (
        not args.articles and not args.all
    )
    do_articles = args.articles or args.all

    if do_events:
        run_events(config, year, month, args)

    if do_articles:
        run_articles(config, year, month, args)

    print("\n完了!")


if __name__ == "__main__":
    main()
