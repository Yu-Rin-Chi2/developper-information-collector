"""Peatix のイベント取得モジュール（Playwright使用）"""

import re
import asyncio
from datetime import datetime
from urllib.parse import quote
from playwright.async_api import async_playwright

from filters import should_exclude, is_relevant
from http_utils import USER_AGENT


SEARCH_URL = "https://peatix.com/search"

MONTH_MAP = {
    "1月": 1, "2月": 2, "3月": 3, "4月": 4,
    "5月": 5, "6月": 6, "7月": 7, "8月": 8,
    "9月": 9, "10月": 10, "11月": 11, "12月": 12,
}

WEEKDAY_MAP_JP = {
    "月曜日": "月", "火曜日": "火", "水曜日": "水", "木曜日": "木",
    "金曜日": "金", "土曜日": "土", "日曜日": "日",
}

WEEKDAY_MAP_EN = {
    "Mon": "月", "Tue": "火", "Wed": "水", "Thu": "木",
    "Fri": "金", "Sat": "土", "Sun": "日",
}


async def fetch_events_async(keywords: list[str], exclude_keywords: list[str],
                             relevance_keywords: list[str] | None = None,
                             location: dict | None = None,
                             max_pages: int = 3) -> list[dict]:
    """Peatixからイベントを取得する（非同期）。

    Args:
        keywords: 検索キーワードリスト
        exclude_keywords: 除外キーワードリスト
        relevance_keywords: 関連性キーワードリスト（タイトルに1つ以上含む必要あり）
        location: {"lat": float, "lng": float} 検索中心座標。Noneの場合はデフォルト
    """
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

        for keyword in keywords:
            url = f"{SEARCH_URL}?lang=ja&q={quote(keyword)}"
            if location:
                url += f"&l.ll={location['lat']},{location['lng']}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception:
                await page.goto(url, timeout=30000)
            await page.wait_for_timeout(5000)

            for _ in range(max_pages):
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

                next_btn = page.get_by_text("次", exact=True)
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    await next_btn.click()
                    await page.wait_for_timeout(5000)
                else:
                    break

        # 参加費情報を各イベント詳細ページから取得
        if all_events:
            print(f"    参加費情報を取得中 ({len(all_events)} 件)...")
            await _fetch_fees(page, all_events)

        await browser.close()

    return all_events


async def _fetch_fees(page, events: list[dict]):
    """各イベントの詳細ページから参加費情報を取得する。"""
    for i, event in enumerate(events):
        url = event.get("url", "")
        if not url:
            continue
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)

            fee = await page.evaluate("""
            () => {
                // 「チケット」セクションからチケット情報を取得
                const headings = document.querySelectorAll('h3');
                for (const h of headings) {
                    if (h.textContent.trim() === 'チケット') {
                        const list = h.closest('div')?.parentElement?.querySelector('ul');
                        if (list) {
                            const items = list.querySelectorAll('li');
                            const tickets = [];
                            for (const item of items) {
                                const text = item.textContent.trim();
                                if (text) tickets.push(text);
                            }
                            if (tickets.length > 0) return tickets.join(' / ');
                        }
                    }
                }

                // フォールバック: ページ全体から料金情報を探す
                const text = document.body.innerText;
                // 「参加費」「参 加 費」パターン
                const feeMatch = text.match(/参\s*加\s*費\s*[：:]\s*(.+)/);
                if (feeMatch) return feeMatch[1].trim().split('\\n')[0];

                // 「料金」パターン
                const priceMatch = text.match(/料\s*金\s*[：:]\s*(.+)/);
                if (priceMatch) return priceMatch[1].trim().split('\\n')[0];

                return '';
            }
            """)

            if fee:
                event["fee"] = _normalize_fee(fee)
        except Exception:
            pass


def _normalize_fee(fee_text: str) -> str:
    """参加費テキストを短く整形する。

    明確な料金情報（無料/金額）がある場合のみ値を返す。
    """
    if not fee_text:
        return ""

    text = fee_text.strip()

    # 無料チェック
    if "無料" in text or "free" in text.lower():
        if "¥" not in text and "円" not in text:
            return "無料"

    # 金額を抽出 (¥1,000 or 1000円 等)
    yen_match = re.search(r"[¥￥][\s]*([0-9,]+)", text)
    if yen_match:
        amount = yen_match.group(1).replace(",", "")
        return f"¥{int(amount):,}"

    en_match = re.search(r"([0-9,]+)\s*円", text)
    if en_match:
        amount = en_match.group(1).replace(",", "")
        return f"¥{int(amount):,}"

    # 明確な金額情報がない場合は空を返す
    return ""


async def _extract_events_from_page(page) -> list[dict]:
    """現在のページからイベント情報をJavaScript経由で抽出する。"""
    events_data = await page.evaluate("""
    () => {
        const results = [];
        const headings = document.querySelectorAll('h2');
        let targetList = null;
        for (const h of headings) {
            if (h.textContent.includes('検索結果')) {
                let sibling = h.nextElementSibling;
                while (sibling) {
                    if (sibling.tagName === 'UL') { targetList = sibling; break; }
                    sibling = sibling.nextElementSibling;
                }
                break;
            }
        }
        if (!targetList) return results;

        const items = targetList.querySelectorAll('li');
        for (const item of items) {
            const link = item.querySelector('a');
            if (!link) continue;

            const href = link.getAttribute('href') || '';
            const url = href.split('?')[0];

            const h3 = item.querySelector('h3');
            const title = h3 ? h3.textContent.trim() : '';

            // innerTextで改行区切りのテキストを取得
            const fullText = link.innerText || '';

            results.push({ url, title, fullText });
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
    url = data.get("url", "")
    title = data.get("title", "")
    full_text = data.get("fullText", "")

    if not url or not title:
        return None

    lines = full_text.split("\n")

    # 日付パース（1行目: "3月 13" or "Mar 13" 等）
    month = 0
    day = 0
    if lines:
        date_line = lines[0].strip()
        # 日本語: "3月 13"
        match = re.match(r"(\d+月)\s*(\d+)", date_line)
        if match:
            month = MONTH_MAP.get(match.group(1), 0)
            day = int(match.group(2))

    # 時間・曜日パース（2行目: "金曜日 19:00" or "Thu, 7:00 PM"）
    day_of_week = ""
    start_time = ""
    if len(lines) >= 2:
        time_line = lines[1].strip()

        # 日本語曜日
        for jp_day, short in WEEKDAY_MAP_JP.items():
            if jp_day in time_line:
                day_of_week = short
                break

        # 英語曜日（フォールバック）
        if not day_of_week:
            for en_day, short in WEEKDAY_MAP_EN.items():
                if en_day in time_line:
                    day_of_week = short
                    break

        # 24時間形式: "19:00"
        time_match = re.search(r"(\d{1,2}):(\d{2})", time_line)
        if time_match:
            hour = int(time_match.group(1))
            minute = time_match.group(2)
            # 12時間表記（AM/PM）対応
            if "PM" in time_line.upper() and hour != 12:
                hour += 12
            elif "AM" in time_line.upper() and hour == 12:
                hour = 0
            start_time = f"{hour:02d}:{minute}"

    # 会場パース（3行目以降: "会場: ○○" or "At ○○" or "オンライン"）
    place = ""
    address = ""
    for line in lines[2:]:
        line = line.strip()
        # 日本語表記
        if line.startswith("会場:") or line.startswith("会場: "):
            venue = line.replace("会場:", "").replace("会場: ", "").strip()
            place = venue
            address = venue
            break
        # 英語表記
        if line.startswith("At "):
            venue = line[3:].strip()
            place = venue
            address = venue
            break
        if line == "オンライン" or line == "Online":
            place = "オンライン"
            address = "オンライン"
            break

    # 年を推定
    date_str = ""
    if month and day:
        now = datetime.now()
        year = now.year
        if month < now.month:
            year += 1
        date_str = f"{year}-{month:02d}-{day:02d}"

    return {
        "title": title,
        "date": date_str,
        "day_of_week": day_of_week,
        "start_time": start_time,
        "end_time": "",
        "place": place,
        "address": address,
        "fee": "",
        "url": url,
        "source": "peatix",
    }


def fetch_events(keywords: list[str], exclude_keywords: list[str],
                 relevance_keywords: list[str] | None = None,
                 location: dict | None = None,
                 max_pages: int = 3) -> list[dict]:
    """Peatixからイベントを取得する（同期ラッパー）。"""
    return asyncio.run(fetch_events_async(
        keywords, exclude_keywords, relevance_keywords, location, max_pages
    ))
