"""connpass 検索ページのイベント取得モジュール（Playwright使用）"""

import re
import asyncio
from datetime import datetime
from urllib.parse import quote
from playwright.async_api import async_playwright

from filters import should_exclude, is_relevant
from http_utils import USER_AGENT


SEARCH_URL = "https://connpass.com/search/"

WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


async def fetch_events_async(keyword: str, start_from: str, start_to: str,
                             exclude_keywords: list[str] | None = None,
                             relevance_keywords: list[str] | None = None,
                             max_pages: int = 3) -> list[dict]:
    """connpass検索ページからイベントを取得する（非同期）。

    Args:
        keyword: 検索キーワード（例: "ゲーム開発"）
        start_from: 開始日 "YYYY/MM/DD" 形式
        start_to: 終了日 "YYYY/MM/DD" 形式
        exclude_keywords: 除外キーワードリスト
        relevance_keywords: 関連性キーワードリスト
        max_pages: 最大ページ数
    """
    exclude_keywords = exclude_keywords or []
    relevance_keywords = relevance_keywords or []
    all_events = []
    seen_urls = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="ja-JP",
        )
        page = await context.new_page()

        url = (f"{SEARCH_URL}?q={quote(keyword)}"
               f"&start_from={quote(start_from)}"
               f"&start_to={quote(start_to)}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            await page.goto(url, timeout=30000)
        await page.wait_for_timeout(3000)

        for page_num in range(max_pages):
            events = await _extract_events_from_page(page)

            for event in events:
                if not event or not event.get("url"):
                    continue
                if event["url"] in seen_urls:
                    continue
                if should_exclude(event["title"], exclude_keywords):
                    continue
                if relevance_keywords and not is_relevant(event["title"], relevance_keywords):
                    continue
                seen_urls.add(event["url"])
                all_events.append(event)

            # ページネーション: 「次へ>>」リンクを探す
            next_link = page.get_by_text("次へ>>")
            if await next_link.count() > 0 and await next_link.is_visible():
                await next_link.click()
                await page.wait_for_timeout(3000)
            else:
                break

        await browser.close()

    return all_events


async def _extract_events_from_page(page) -> list[dict]:
    """現在のページからイベント情報をJavaScript経由で抽出する。"""
    events_data = await page.evaluate("""
    () => {
        const results = [];
        // イベントカードは div.event_list.vevent クラスで特定
        const cards = document.querySelectorAll('div.event_list.vevent');

        for (const card of cards) {
            // 日付エリア: div.event_schedule_area
            const schedule = card.querySelector('.event_schedule_area');
            const year = schedule?.querySelector('.year')?.textContent?.trim() || '';
            const monthDay = schedule?.querySelector('.date')?.textContent?.trim() || '';
            const dowTime = schedule?.querySelector('.time')?.textContent?.trim() || '';

            // タイトル + URL: a.url.summary
            const titleLink = card.querySelector('a.url.summary');
            const title = titleLink?.textContent?.trim() || '';
            let url = titleLink?.getAttribute('href') || '';
            if (url && !url.startsWith('http')) {
                url = 'https://connpass.com' + url;
            }

            // 住所: p.event_place.location
            const placeEl = card.querySelector('.event_place.location');
            const address = placeEl?.textContent?.trim() || '';

            // 参加者数: p.event_participants
            const partEl = card.querySelector('.event_participants');
            const participants = partEl?.textContent?.trim() || '';

            if (title && url) {
                results.push({
                    year, monthDay, dowTime, title, url, address, participants
                });
            }
        }
        return results;
    }
    """)

    events = []
    for data in events_data:
        event = _parse_event_data(data)
        if event:
            events.append(event)

    return events


def _parse_event_data(data: dict) -> dict | None:
    """JavaScript抽出データを共通フォーマットに変換する。"""
    title = data.get("title", "")
    url = data.get("url", "")
    if not title or not url:
        return None

    year = data.get("year", "")
    month_day = data.get("monthDay", "")  # "02/22"
    dow_time = data.get("dowTime", "")    # "（日）10:30〜"
    address = data.get("address", "")

    # 日付
    date_str = ""
    if year and month_day:
        date_str = f"{year}-{month_day.replace('/', '-')}"

    # 曜日
    day_of_week = ""
    dow_match = re.search(r"[（(]([月火水木金土日])[）)]", dow_time)
    if dow_match:
        day_of_week = dow_match.group(1)

    # 開始時間
    start_time = ""
    time_match = re.search(r"(\d{1,2}:\d{2})", dow_time)
    if time_match:
        start_time = time_match.group(1)
        # 1桁時間を2桁に
        if len(start_time) == 4:
            start_time = "0" + start_time

    return {
        "title": title,
        "date": date_str,
        "day_of_week": day_of_week,
        "start_time": start_time,
        "end_time": "",
        "place": address,
        "address": address,
        "fee": "",
        "url": url,
        "source": "connpass",
    }


def fetch_and_parse(keyword: str, start_from: str, start_to: str,
                    exclude_keywords: list[str] | None = None,
                    relevance_keywords: list[str] | None = None,
                    max_pages: int = 3) -> list[dict]:
    """connpass検索ページからイベントを取得する（同期ラッパー）。

    Args:
        keyword: 検索キーワード
        start_from: 開始日 "YYYY/MM/DD" 形式
        start_to: 終了日 "YYYY/MM/DD" 形式
    """
    return asyncio.run(fetch_events_async(
        keyword, start_from, start_to,
        exclude_keywords, relevance_keywords, max_pages
    ))
