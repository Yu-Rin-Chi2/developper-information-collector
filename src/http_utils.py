"""共通HTTP/ネットワークユーティリティ"""

import time
import requests


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {"User-Agent": USER_AGENT}


def request_with_retry(url: str, headers: dict | None = None,
                       max_retries: int = 3, backoff_base: float = 2.0,
                       timeout: int = 30) -> requests.Response:
    """リトライ付きHTTPリクエスト（指数バックオフ）。"""
    headers = headers or DEFAULT_HEADERS
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (requests.RequestException, requests.HTTPError) as e:
            if attempt == max_retries - 1:
                raise
            wait = backoff_base ** attempt
            print(f"  リトライ ({attempt + 1}/{max_retries}): {wait}秒後に再試行...")
            time.sleep(wait)
