"""Qiita API v2 を使った記事取得モジュール"""

import re
import time
from datetime import datetime
from urllib.parse import quote

from filters import should_exclude, is_relevant
from http_utils import request_with_retry, DEFAULT_HEADERS


QIITA_API_BASE = "https://qiita.com/api/v2/items"


def fetch_articles(queries: list[str],
                   exclude_keywords: list[str] | None = None,
                   relevance_keywords: list[str] | None = None,
                   per_page: int = 20,
                   max_pages: int = 2,
                   category: str = "") -> list[dict]:
    """Qiita API v2 から記事を取得する。

    Args:
        queries: 検索クエリリスト（例: ["tag:Unity フリー素材"]）
        exclude_keywords: 除外キーワードリスト
        relevance_keywords: 関連性キーワードリスト
        per_page: 1ページあたりの件数（最大100）
        max_pages: 最大ページ数
        category: カテゴリ名（free-assets, learning-resources, peripherals）

    Returns:
        記事情報の辞書リスト
    """
    exclude_keywords = exclude_keywords or []
    relevance_keywords = relevance_keywords or []
    all_articles = []
    seen_urls = set()

    for query in queries:
        for page in range(1, max_pages + 1):
            url = (f"{QIITA_API_BASE}"
                   f"?query={quote(query)}"
                   f"&per_page={per_page}"
                   f"&page={page}")
            try:
                resp = request_with_retry(url, headers=DEFAULT_HEADERS)
                items = resp.json()
            except Exception as e:
                print(f"    Qiita API エラー ({query}): {e}")
                break

            if not items or not isinstance(items, list):
                break

            for item in items:
                article = _parse_item(item, category)
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

            time.sleep(1)

    return all_articles


def _parse_item(item: dict, category: str) -> dict | None:
    """Qiita API レスポンスを記事辞書に変換する。"""
    title = item.get("title", "")
    url = item.get("url", "")
    if not title or not url:
        return None

    user = item.get("user", {})
    author = user.get("id", "")

    created = item.get("created_at", "")
    published_date = ""
    if created:
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            published_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    tags = [t.get("name", "") for t in item.get("tags", []) if t.get("name")]

    body = item.get("body", "")
    summary = _extract_summary(body)

    return {
        "title": title,
        "url": url,
        "author": author,
        "published_date": published_date,
        "tags": tags,
        "likes_count": item.get("likes_count", 0),
        "summary": summary,
        "source": "qiita",
        "category": category,
    }


def _extract_summary(body: str, max_length: int = 200) -> str:
    """Markdown本文から概要テキストを抽出する。"""
    text = re.sub(r'[#*`\[\]()>|~_-]', '', body)
    text = re.sub(r'\n+', ' ', text).strip()
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text
