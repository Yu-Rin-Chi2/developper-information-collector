"""こくちーずプロ のイベント取得モジュール（requests + BeautifulSoup）"""

import re
from bs4 import BeautifulSoup

from filters import should_exclude, is_relevant
from http_utils import request_with_retry, DEFAULT_HEADERS

WEEKDAY_MAP = {
    "月": "月", "火": "火", "水": "水", "木": "木",
    "金": "金", "土": "土", "日": "日",
}


def fetch_events(base_url: str, exclude_keywords: list[str] | None = None,
                 relevance_keywords: list[str] | None = None) -> list[dict]:
    """こくちーずプロからイベントを取得する。

    Args:
        base_url: 特集ページのURL
        exclude_keywords: 除外キーワードリスト
        relevance_keywords: 関連性キーワードリスト
    """
    exclude_keywords = exclude_keywords or []
    relevance_keywords = relevance_keywords or []

    resp = request_with_retry(base_url)

    soup = BeautifulSoup(resp.text, "html.parser")
    event_items = soup.select("div.event_item")

    events = []
    for item in event_items:
        event = _parse_event_item(item)
        if not event:
            continue
        if should_exclude(event["title"], exclude_keywords):
            continue
        if relevance_keywords and not is_relevant(event["title"], relevance_keywords):
            continue
        events.append(event)

    return events


def _parse_event_item(item) -> dict | None:
    """1件のイベントカード(div.event_item)をパースする。"""
    # タイトル + URL
    name_wrapper = item.select_one("div.event_name_wrapper a")
    if not name_wrapper:
        return None
    title = name_wrapper.get_text(strip=True)
    url = name_wrapper.get("href", "")
    if url and not url.startswith("http"):
        url = "https://www.kokuchpro.com" + url

    # テーブルから詳細情報を取得（<th>キー + <td>値 の構造）
    table = item.select_one("table.event_table")
    table_data = {}
    if table:
        for row in table.select("tr"):
            th = row.select_one("th")
            td = row.select_one("td")
            if th and td:
                key = th.get_text(strip=True)
                value = td.get_text(strip=True)
                table_data[key] = value

    # 開催日パース: "2026年3月3日(火) 19:00〜20:30"
    date_str = ""
    day_of_week = ""
    start_time = ""
    end_time = ""

    date_text = table_data.get("開催日", "")
    if date_text:
        date_str, day_of_week, start_time, end_time = _parse_date_text(date_text)

    # 開催場所パース: "レアル会議室(大会議室) （東京都）"
    place = ""
    address = ""
    place_text = table_data.get("開催場所", "")
    if place_text:
        place, address = _parse_place_text(place_text)

    if not title:
        return None

    return {
        "title": title,
        "date": date_str,
        "day_of_week": day_of_week,
        "start_time": start_time,
        "end_time": end_time,
        "place": place,
        "address": address,
        "fee": "",
        "url": url,
        "source": "kokuchpro",
    }


def _parse_date_text(text: str) -> tuple[str, str, str, str]:
    """開催日テキストから日付・曜日・時間を抽出する。

    入力例:
        "2026年3月3日(火) 19:00〜20:30"
        "2025年10月9日(木) 10:00〜2026年2月26日(木) 17:00"

    Returns:
        (date_str, day_of_week, start_time, end_time)
    """
    date_str = ""
    day_of_week = ""
    start_time = ""
    end_time = ""

    # 日付: "YYYY年M月D日"
    date_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if date_match:
        year = int(date_match.group(1))
        month = int(date_match.group(2))
        day = int(date_match.group(3))
        date_str = f"{year}-{month:02d}-{day:02d}"

    # 曜日: "(火)" 等
    dow_match = re.search(r"[（(]([月火水木金土日])[）)]", text)
    if dow_match:
        day_of_week = dow_match.group(1)

    # 時間: "19:00〜20:30" or "19:00～20:30"
    # まず開始日側の時間を取得
    time_match = re.search(r"(\d{1,2}:\d{2})\s*[〜～]\s*(\d{1,2}:\d{2})", text)
    if time_match:
        start_time = time_match.group(1)
        end_time = time_match.group(2)
    else:
        # 開始時間のみ（長期開催等で終了日が別の日のケース）
        single_time = re.search(r"(\d{1,2}:\d{2})", text)
        if single_time:
            start_time = single_time.group(1)

    return date_str, day_of_week, start_time, end_time


def _parse_place_text(text: str) -> tuple[str, str]:
    """開催場所テキストから場所名と住所（都道府県）を抽出する。

    入力例:
        "レアル会議室(大会議室) （東京都）"
        "(株)ハートフルコミュニケーションズ （愛知県）"

    Returns:
        (place, address)
    """
    # 全角括弧内の都道府県を抽出
    pref_match = re.search(r"（(.+?[都道府県])）", text)
    address = pref_match.group(1) if pref_match else ""

    # 場所名: 都道府県の括弧部分を除去
    place = re.sub(r"\s*（.+?[都道府県]）\s*", "", text).strip()

    # address が空なら place をそのまま使用
    if not address:
        address = place

    return place, address


