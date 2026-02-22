"""Note.com の記事取得モジュール（内部API利用）

Note.com の内部API v3 を利用してJSON形式で検索結果を取得する。
"""

import re
import time
from urllib.parse import quote

from filters import should_exclude, is_relevant
from http_utils import request_with_retry, DEFAULT_HEADERS


NOTE_API_URL = "https://note.com/api/v3/searches"


def fetch_articles(queries: list[str],
                   exclude_keywords: list[str] | None = None,
                   relevance_keywords: list[str] | None = None,
                   max_pages: int = 2,
                   category: str = "") -> list[dict]:
    """Note.com から記事を検索・取得する。

    Args:
        queries: 検索キーワードリスト
        exclude_keywords: 除外キーワードリスト
        relevance_keywords: 関連性キーワードリスト
        max_pages: 最大ページ数
        category: カテゴリ名

    Returns:
        記事情報の辞書リスト
    """
    exclude_keywords = exclude_keywords or []
    relevance_keywords = relevance_keywords or []
    all_articles = []
    seen_urls = set()

    for query in queries:
        for page in range(1, max_pages + 1):
            url = (f"{NOTE_API_URL}"
                   f"?q={quote(query)}"
                   f"&size=20"
                   f"&start={20 * (page - 1)}"
                   f"&sort=new"
                   f"&context=note")
            try:
                resp = request_with_retry(url, headers=DEFAULT_HEADERS)
                data = resp.json()
            except Exception as e:
                print(f"    Note.com API エラー ({query}): {e}")
                break

            notes = data.get("data", {}).get("notes", {}).get("contents", [])
            if not notes:
                break

            for item in notes:
                article = _parse_note_item(item, category)
                if not article:
                    continue
                if article["url"] in seen_urls:
                    continue
                if should_exclude(article["title"], exclude_keywords):
                    continue
                if relevance_keywords and not is_relevant(article["title"], relevance_keywords):
                    continue
                seen_urls.add(article["url"])
                all_articles.append(article)

            # 次ページがあるか確認
            is_last = data.get("data", {}).get("notes", {}).get("is_last_page", True)
            if is_last:
                break

            time.sleep(1.5)

    return all_articles


def _parse_note_item(item: dict, category: str) -> dict | None:
    """Note.com API レスポンスを記事辞書に変換する。"""
    name = item.get("name", "")
    key = item.get("key", "")
    user = item.get("user", {}) or {}
    urlname = user.get("urlname", "")

    if not name or not key or not urlname:
        return None

    # URL構築: https://note.com/{urlname}/n/{key}
    note_url = f"https://note.com/{urlname}/n/{key}"

    author = urlname or user.get("nickname", "")

    published = item.get("publish_at", "")
    published_date = ""
    if published:
        try:
            date_part = published[:10]
            if re.match(r"\d{4}-\d{2}-\d{2}", date_part):
                published_date = date_part
        except (ValueError, IndexError):
            pass

    likes = item.get("like_count", 0)

    # 概要（descriptionフィールドを使用）
    description = item.get("description", "") or ""
    summary = ""
    if description:
        text = re.sub(r'<[^>]+>', '', description)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 200:
            text = text[:200] + "..."
        summary = text

    return {
        "title": name,
        "url": note_url,
        "author": author,
        "published_date": published_date,
        "tags": [],
        "likes_count": likes,
        "summary": summary,
        "source": "note",
        "category": category,
    }
