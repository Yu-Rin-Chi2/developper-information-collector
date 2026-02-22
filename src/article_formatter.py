"""記事情報をDiscord向けMarkdownに整形するモジュール"""

import os
from datetime import datetime


CATEGORY_LABELS = {
    "free-assets": "ゲーム用フリーアセットまとめ記事",
    "learning-resources": "Unity学習リソース記事",
    "peripherals": "ゲーム開発周辺機器レビュー記事",
}

SOURCE_LABELS = {
    "qiita": "Qiita",
    "zenn": "Zenn",
    "note": "Note",
}


def format_article_list(articles: list[dict], category: str,
                        year: int, month: int) -> str:
    """記事リストをDiscord向けMarkdownに変換する。

    Args:
        articles: 記事情報の辞書リスト
        category: カテゴリキー
        year: 対象年
        month: 対象月

    Returns:
        Markdown文字列
    """
    label = CATEGORY_LABELS.get(category, category)

    # いいね数でソート（降順：人気順）
    sorted_articles = sorted(
        articles,
        key=lambda a: a.get("likes_count", 0),
        reverse=True
    )

    lines = []
    lines.append(f"# {label} ({year}年{month}月収集)")
    lines.append("")

    if not sorted_articles:
        lines.append("該当する記事はありません。")
        lines.append("")
    else:
        for i, article in enumerate(sorted_articles, 1):
            lines.append(_format_article(article, i))
            lines.append("")

    lines.append("---")
    now = datetime.now()
    lines.append(f"最終更新: {now.strftime('%Y/%m/%d %H:%M')}")
    lines.append("")

    return "\n".join(lines)


def _format_article(article: dict, index: int) -> str:
    """1件の記事をフォーマットする。

    出力例:
        **1.** [Unity初心者向け無料アセットまとめ2026](https://qiita.com/xxx)
        └ @author_name ｜ 2026/03/05 ｜ 42 likes ｜ Qiita
        └ タグ: Unity, ゲーム開発, フリー素材
    """
    title = article.get("title", "")
    url = article.get("url", "")
    author = article.get("author", "")
    published_date = article.get("published_date", "")
    likes = article.get("likes_count", 0)
    source = article.get("source", "")
    tags = article.get("tags", [])

    # 日付を整形
    date_display = ""
    if published_date:
        parts = published_date.split("-")
        if len(parts) == 3:
            date_display = f"{parts[0]}/{parts[1]}/{parts[2]}"

    source_label = SOURCE_LABELS.get(source, source)

    # 1行目: 番号 + タイトルリンク
    header = f"**{index}.** [{title}]({url})"

    # 2行目: 著者 | 日付 | いいね数 | ソース
    detail_parts = []
    if author:
        detail_parts.append(f"@{author}")
    if date_display:
        detail_parts.append(date_display)
    if likes > 0:
        detail_parts.append(f"{likes} likes")
    if source_label:
        detail_parts.append(source_label)

    detail_line = f"└ {' ｜ '.join(detail_parts)}" if detail_parts else ""

    # 3行目（任意）: タグ
    tag_line = ""
    if tags:
        tag_line = f"└ タグ: {', '.join(tags[:5])}"

    parts = [header]
    if detail_line:
        parts.append(detail_line)
    if tag_line:
        parts.append(tag_line)

    return "\n".join(parts)


def save_article_list(articles: list[dict], category: str,
                      year: int, month: int, output_dir: str) -> str:
    """記事リストMarkdownをファイルに保存する。

    Returns:
        保存したファイルパス
    """
    category_dir = os.path.join(output_dir, category)
    os.makedirs(category_dir, exist_ok=True)

    content = format_article_list(articles, category, year, month)
    filename = f"{year}-{month:02d}_{category}.md"
    filepath = os.path.join(category_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath
