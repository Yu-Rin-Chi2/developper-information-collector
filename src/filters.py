"""共通のテキストフィルタリングモジュール"""

import re


def should_exclude(title: str, exclude_keywords: list[str]) -> bool:
    """タイトルに除外キーワードが含まれるか判定する。"""
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in exclude_keywords)


def is_relevant(title: str, relevance_keywords: list[str]) -> bool:
    """タイトルに関連性キーワードが1つ以上含まれるか判定する。

    ASCIIキーワードは単語境界を考慮して部分文字列の誤マッチを防ぐ。
    例: "unity" in "community", "ar" in "Sphear" -> マッチしない
    日本語キーワードは通常の部分文字列マッチを使用。
    """
    title_lower = title.lower()
    for kw in relevance_keywords:
        kw_lower = kw.lower()
        if kw_lower.isascii():
            if re.search(
                r'(?<![a-zA-Z])' + re.escape(kw_lower) + r'(?![a-zA-Z])',
                title_lower
            ):
                return True
        else:
            if kw_lower in title_lower:
                return True
    return False
