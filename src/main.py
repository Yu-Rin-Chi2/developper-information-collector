"""ゲーム開発イベント収集ツール メインスクリプト

Usage:
    python src/main.py                    # 来月のイベントを取得
    python src/main.py --month 202603     # 2026年3月のイベントを取得
    python src/main.py --connpass-only    # connpassのみ
    python src/main.py --peatix-only      # Peatixのみ
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime

# Windows cp932 文字化け対策
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper_connpass import fetch_and_parse as connpass_fetch
from scraper_peatix import fetch_events as peatix_fetch
from classifier import classify_events
from formatter import save_calendar


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "sites.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")


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


def collect_connpass_events(config: dict, ym: str, api_key: str) -> list[dict]:
    """connpassからイベントを収集する。"""
    connpass_config = config.get("connpass", {})
    keywords = connpass_config.get("keywords", ["ゲーム開発"])

    all_events = []
    for keyword in keywords:
        print(f"  connpass: キーワード '{keyword}' で検索中...")
        events = connpass_fetch(api_key, keyword, ym)
        all_events.extend(events)
        print(f"  → {len(events)} 件取得")

    return all_events


def collect_peatix_events(config: dict) -> list[dict]:
    """Peatixからイベントを収集する（各地域の座標で検索）。"""
    peatix_config = config.get("peatix", {})
    keywords = peatix_config.get("keywords", ["ゲーム開発"])
    exclude = peatix_config.get("exclude_keywords", [])
    locations = peatix_config.get("locations", {})

    all_events = []
    seen_urls = set()

    for region_key, location in locations.items():
        region_label = config.get("regions", {}).get(region_key, {}).get("label", region_key)
        print(f"  Peatix ({region_label}): キーワード {keywords} で検索中...")
        events = peatix_fetch(keywords, exclude, location=location)
        new_count = 0
        for event in events:
            if event["url"] not in seen_urls:
                seen_urls.add(event["url"])
                all_events.append(event)
                new_count += 1
        print(f"  → {new_count} 件取得 (重複除外済)")

    return all_events


def main():
    parser = argparse.ArgumentParser(description="ゲーム開発イベント収集ツール")
    parser.add_argument("--month", type=str, default=None,
                        help="対象年月 (YYYYMM形式, デフォルト: 来月)")
    parser.add_argument("--connpass-only", action="store_true",
                        help="connpassのみ取得")
    parser.add_argument("--peatix-only", action="store_true",
                        help="Peatixのみ取得")
    parser.add_argument("--api-key", type=str, default=None,
                        help="connpass APIキー（環境変数 CONNPASS_API_KEY でも可）")
    args = parser.parse_args()

    # APIキー
    api_key = args.api_key or os.environ.get("CONNPASS_API_KEY", "")

    # 対象月
    year, month = get_target_month(args.month)
    ym = f"{year}{month:02d}"
    print(f"対象: {year}年{month}月")

    # 設定読み込み
    config = load_config()

    # イベント収集
    all_events = []

    if not args.peatix_only:
        if not api_key:
            print("警告: connpass APIキーが未設定です。"
                  "環境変数 CONNPASS_API_KEY または --api-key で指定してください。")
            print("connpassのスクレイピングをスキップします。")
        else:
            events = collect_connpass_events(config, ym, api_key)
            all_events.extend(events)

    if not args.connpass_only:
        try:
            events = collect_peatix_events(config)
            all_events.extend(events)
        except Exception as e:
            print(f"警告: Peatixの取得に失敗しました: {e}")
            print("Playwrightがインストールされているか確認してください:")
            print("  pip install playwright && playwright install chromium")

    print(f"\n合計: {len(all_events)} 件のイベントを取得")

    # 地域分類
    classified = classify_events(all_events)

    for region in ["kanto", "kansai"]:
        events = classified[region]
        print(f"\n{region}: {len(events)} 件")

        filepath = save_calendar(events, region, year, month, OUTPUT_DIR)
        print(f"  → {filepath}")

    other_count = len(classified.get("other", []))
    if other_count > 0:
        print(f"\nその他（地域不明/オンライン）: {other_count} 件")

    print("\n完了!")


if __name__ == "__main__":
    main()
