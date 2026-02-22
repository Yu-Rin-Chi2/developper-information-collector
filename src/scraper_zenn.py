"""Zenn API を使った記事取得モジュール"""

import time
from datetime import datetime
from urllib.parse import quote

from filters import should_exclude, is_relevant
from http_utils import request_with_retry, DEFAULT_HEADERS


ZENN_API_BASE = "https://zenn.dev/api/articles"
ZENN_BASE_URL = "https://zenn.dev"


def fetch_articles(topic_queries: list[dict],
                   exclude_keywords: list[str] | None = None,
                   relevance_keywords: list[str] | None = None,
                   max_pages: int = 2,
                   category: str = "") -> list[dict]:
    """Zenn API から記事を取得する。

    Args:
        topic_queries: クエリリスト。各要素は:
            {"topicname": "unity", "order": "latest"} or
            {"keyword": "フリーアセット", "order": "latest"}
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

    for query in topic_queries:
        for page in range(1, max_pages + 1):
            params = f"?page={page}&order={query.get('order', 'latest')}"
            if "topicname" in query:
                params += f"&topicname={quote(query['topicname'])}"
            if "keyword" in query:
                params += f"&keyword={quote(query['keyword'])}"

            url = f"{ZENN_API_BASE}{params}"
            try:
                resp = request_with_retry(url, headers=DEFAULT_HEADERS)
                data = resp.json()
            except Exception as e:
                print(f"    Zenn API エラー: {e}")
                break

            articles = data.get("articles", [])
            if not articles:
                break

            for item in articles:
                article = _parse_article(item, category)
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

            next_page = data.get("next_page")
            if not next_page:
                break

            time.sleep(1)

    return all_articles


def _parse_article(item: dict, category: str) -> dict | None:
    """Zenn API レスポンスを記事辞書に変換する。"""
    title = item.get("title", "")
    path = item.get("path", "")
    if not title or not path:
        return None

    url = f"{ZENN_BASE_URL}{path}"
    user = item.get("user", {})
    author = user.get("username", "") or user.get("name", "")

    published = item.get("published_at", "")
    published_date = ""
    if published:
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            published_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return {
        "title": title,
        "url": url,
        "author": author,
        "published_date": published_date,
        "tags": [],
        "likes_count": item.get("liked_count", 0),
        "summary": "",
        "source": "zenn",
        "category": category,
    }
