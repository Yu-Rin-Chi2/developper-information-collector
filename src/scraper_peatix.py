"""Peatix のイベント取得モジュール（Playwright使用）"""

import re
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright


SEARCH_URL = "https://peatix.com/search"

# 月名 → 月番号のマッピング
MONTH_MAP = {
    "1月": 1, "2月": 2, "3月": 3, "4月": 4,
    "5月": 5, "6月": 6, "7月": 7, "8月": 8,
    "9月": 9, "10月": 10, "11月": 11, "12月": 12,
}

WEEKDAY_MAP = {
    "月曜日": "月", "火曜日": "火", "水曜日": "水", "木曜日": "木",
    "金曜日": "金", "土曜日": "土", "日曜日": "日",
}


async def fetch_events_async(keywords: list[str], exclude_keywords: list[str],
                             max_pages: int = 3) -> list[dict]:
    """Peatixからイベントを取得する（非同期）。

    Args:
        keywords: 検索キーワードリスト（それぞれ個別に検索）
        exclude_keywords: 除外キーワードリスト
        max_pages: キーワードあたりの最大ページ数

    Returns:
        イベント情報の辞書リスト
    """
    all_events = []
    seen_urls = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for keyword in keywords:
            url = f"{SEARCH_URL}?lang=ja&q={keyword}"
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)  # SPA描画待ち

            for page_num in range(max_pages):
                events = await _extract_events_from_page(page)

                for event in events:
                    if event["url"] in seen_urls:
                        continue
                    if _should_exclude(event["title"], exclude_keywords):
                        continue
                    seen_urls.add(event["url"])
                    all_events.append(event)

                # 次ページへ
                next_btn = page.locator('div:text("次")')
                if await next_btn.count() > 0:
                    await next_btn.click()
                    await page.wait_for_timeout(3000)
                else:
                    break

        await browser.close()

    return all_events


async def _extract_events_from_page(page) -> list[dict]:
    """現在のページからイベント情報を抽出する。"""
    events = []

    # 検索結果のリストアイテムを取得
    items = page.locator('h2:text("検索結果") ~ ul > li')
    count = await items.count()

    for i in range(count):
        item = items.nth(i)
        try:
            event = await _parse_event_item(item)
            if event:
                events.append(event)
        except Exception:
            continue

    return events


async def _parse_event_item(item) -> dict | None:
    """リストアイテムからイベント情報をパースする。"""
    # リンク要素（全情報を含む）
    link = item.locator("a").first
    if await link.count() == 0:
        return None

    href = await link.get_attribute("href") or ""
    # URLからUTMパラメータ等を除去
    url = href.split("?")[0] if href else ""
    if not url:
        return None

    # テキスト全体を取得
    full_text = await link.inner_text()

    # タイトル（h3タグ）
    title_el = item.locator("h3")
    title = (await title_el.inner_text()).strip() if await title_el.count() > 0 else ""

    # 日時を抽出（timeタグ）
    time_elements = item.locator("time")
    time_count = await time_elements.count()

    date_str = ""
    day_of_week = ""
    start_time = ""
    month = 0
    day = 0

    if time_count >= 1:
        # 最初のtime: "3月 13" のような日付
        date_text = (await time_elements.nth(0).inner_text()).strip()
        match = re.match(r"(\d+月)\s*(\d+)", date_text)
        if match:
            month = MONTH_MAP.get(match.group(1), 0)
            day = int(match.group(2))

    if time_count >= 2:
        # 2つ目のtime: "金曜日 18:00" のような曜日+時間
        time_text = (await time_elements.nth(1).inner_text()).strip()
        for jp_day, short in WEEKDAY_MAP.items():
            if jp_day in time_text:
                day_of_week = short
                break
        time_match = re.search(r"(\d{1,2}:\d{2})", time_text)
        if time_match:
            start_time = time_match.group(1)

    # 日付文字列を構築（年は現在年を仮定、月が過去なら翌年）
    if month and day:
        now = datetime.now()
        year = now.year
        if month < now.month:
            year += 1
        date_str = f"{year}-{month:02d}-{day:02d}"

    # 会場情報を抽出
    place = ""
    address = ""
    lines = full_text.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("会場:") or line.startswith("会場: "):
            venue_text = line.replace("会場:", "").replace("会場: ", "").strip()
            place = venue_text
            address = venue_text
            break
        elif line == "オンライン":
            place = "オンライン"
            address = "オンライン"
            break

    return {
        "title": title,
        "date": date_str,
        "day_of_week": day_of_week,
        "start_time": start_time,
        "end_time": "",  # Peatixの検索結果では終了時間が表示されない
        "place": place,
        "address": address,
        "fee": "",  # 検索結果一覧には参加費が表示されない
        "url": url,
        "source": "peatix",
    }


def _should_exclude(title: str, exclude_keywords: list[str]) -> bool:
    """タイトルに除外キーワードが含まれるか判定する。"""
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in exclude_keywords)


def fetch_events(keywords: list[str], exclude_keywords: list[str],
                 max_pages: int = 3) -> list[dict]:
    """Peatixからイベントを取得する（同期ラッパー）。"""
    return asyncio.run(fetch_events_async(keywords, exclude_keywords, max_pages))
