"""connpass API v2 を使ったイベント取得モジュール"""

import time
import requests


API_BASE = "https://connpass.com/api/v2/events/"


def fetch_events(api_key: str, keyword: str, ym: str, prefecture: str | None = None,
                 count: int = 100) -> list[dict]:
    """connpass API v2 からイベントを取得する。

    Args:
        api_key: connpass API キー
        keyword: 検索キーワード（例: "ゲーム開発"）
        ym: 対象年月 yyyymm 形式（例: "202603"）
        prefecture: 都道府県名（例: "東京都"）。None の場合フィルタなし
        count: 1回のリクエストで取得する件数（最大100）

    Returns:
        イベント情報の辞書リスト
    """
    all_events = []
    start = 1

    while True:
        params = {
            "keyword": keyword,
            "ym": ym,
            "order": 2,  # 開催日順
            "count": count,
            "start": start,
        }
        if prefecture:
            params["prefecture"] = prefecture

        headers = {"X-API-Key": api_key}

        resp = requests.get(API_BASE, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        events = data.get("events", [])
        all_events.extend(events)

        results_available = data.get("results_available", 0)
        results_returned = data.get("results_returned", 0)

        if start + results_returned > results_available:
            break

        start += results_returned
        time.sleep(1)  # レートリミット: 1秒間に1リクエスト

    return all_events


def parse_event(event: dict) -> dict:
    """API レスポンスのイベントを共通フォーマットに変換する。

    Returns:
        {
            "title": str,
            "date": str (YYYY-MM-DD),
            "day_of_week": str (月, 火, ...),
            "start_time": str (HH:MM),
            "end_time": str (HH:MM) or "",
            "place": str,
            "address": str,
            "fee": str,
            "url": str,
            "source": "connpass",
        }
    """
    from datetime import datetime

    started = event.get("started_at", "")
    ended = event.get("ended_at", "")

    weekdays = ["月", "火", "水", "木", "金", "土", "日"]

    date_str = ""
    day_of_week = ""
    start_time = ""
    if started:
        dt = datetime.fromisoformat(started)
        date_str = dt.strftime("%Y-%m-%d")
        day_of_week = weekdays[dt.weekday()]
        start_time = dt.strftime("%H:%M")

    end_time = ""
    if ended:
        dt_end = datetime.fromisoformat(ended)
        end_time = dt_end.strftime("%H:%M")

    return {
        "title": event.get("title", ""),
        "date": date_str,
        "day_of_week": day_of_week,
        "start_time": start_time,
        "end_time": end_time,
        "place": event.get("place", "") or "",
        "address": event.get("address", "") or "",
        "fee": "",  # connpass API にはfeeフィールドがないため空
        "url": event.get("url", ""),
        "source": "connpass",
    }


def fetch_and_parse(api_key: str, keyword: str, ym: str,
                    prefecture: str | None = None) -> list[dict]:
    """取得 + パースをまとめて実行する。"""
    raw_events = fetch_events(api_key, keyword, ym, prefecture)
    return [parse_event(e) for e in raw_events]
