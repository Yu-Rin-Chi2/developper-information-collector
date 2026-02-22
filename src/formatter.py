"""イベント情報をMarkdownカレンダー形式に整形するモジュール"""

import os
from datetime import datetime


REGION_LABELS = {
    "kanto": "関東",
    "kansai": "関西",
}


def format_calendar(events: list[dict], region: str, year: int, month: int) -> str:
    """イベントリストを月刊カレンダー形式のMarkdownに変換する。

    Args:
        events: イベント情報の辞書リスト（共通フォーマット）
        region: 地域キー ("kanto" or "kansai")
        year: 対象年
        month: 対象月

    Returns:
        Markdown文字列
    """
    region_label = REGION_LABELS.get(region, region)

    # 対象月のイベントのみフィルタ
    target_prefix = f"{year}-{month:02d}"
    monthly_events = [
        e for e in events
        if e.get("date", "").startswith(target_prefix)
    ]

    # 日付順にソート
    monthly_events.sort(key=lambda e: (e.get("date", ""), e.get("start_time", "")))

    lines = []
    lines.append(f"# {year}年{month}月 {region_label}ゲーム開発イベント")
    lines.append("")

    if not monthly_events:
        lines.append("該当するイベントはありません。")
        lines.append("")
    else:
        for event in monthly_events:
            lines.append(_format_event(event, year))
            lines.append("")

    lines.append("---")
    now = datetime.now()
    lines.append(f"最終更新: {now.strftime('%Y/%m/%d %H:%M')}")
    lines.append("")

    return "\n".join(lines)


def _format_event(event: dict, year: int) -> str:
    """1件のイベントをフォーマットする。

    出力例:
        **3/5(木)** Unity Meetup Tokyo #42
        └ 19:00-21:00 ｜ 渋谷 ｜ 無料
        └ https://connpass.com/event/xxxxx
    """
    date_str = event.get("date", "")
    day_of_week = event.get("day_of_week", "")
    start_time = event.get("start_time", "")
    end_time = event.get("end_time", "")
    title = event.get("title", "")
    place = event.get("place", "")
    fee = event.get("fee", "")
    url = event.get("url", "")

    # 日付を "3/5" 形式に
    date_short = ""
    if date_str:
        parts = date_str.split("-")
        if len(parts) == 3:
            m = int(parts[1])
            d = int(parts[2])
            date_short = f"{m}/{d}"

    # 時間帯
    time_range = start_time
    if start_time and end_time:
        time_range = f"{start_time}-{end_time}"

    # 場所を短縮（住所から主要エリア名のみ抽出）
    place_short = _shorten_place(place)

    # 費用
    fee_str = fee if fee else ""

    # 1行目: 日付 + タイトル
    header = f"**{date_short}({day_of_week})** {title}"

    # 2行目: 時間 | 場所 | 費用
    detail_parts = []
    if time_range:
        detail_parts.append(time_range)
    if place_short:
        detail_parts.append(place_short)
    if fee_str:
        detail_parts.append(fee_str)

    detail_line = f"└ {' ｜ '.join(detail_parts)}" if detail_parts else ""

    # 3行目: URL
    url_line = f"└ {url}" if url else ""

    parts = [header]
    if detail_line:
        parts.append(detail_line)
    if url_line:
        parts.append(url_line)

    return "\n".join(parts)


def _shorten_place(place: str) -> str:
    """場所文字列を短縮する（主要エリア名のみ）。"""
    if not place or place == "オンライン":
        return place

    # 「東京都渋谷区...」→ 「渋谷」のようなパターン
    # 区名を抽出
    import re
    match = re.search(r"([^\s]+[区市町村])", place)
    if match:
        area = match.group(1)
        # 「渋谷区」→「渋谷」
        for suffix in ["区", "市", "町", "村"]:
            if area.endswith(suffix) and len(area) > len(suffix) + 1:
                return area[:-len(suffix)]
        return area

    # 短い場所名はそのまま返す
    if len(place) <= 10:
        return place

    return place[:10]


def save_calendar(events: list[dict], region: str, year: int, month: int,
                  output_dir: str) -> str:
    """カレンダーMarkdownをファイルに保存する。

    Returns:
        保存したファイルパス
    """
    os.makedirs(output_dir, exist_ok=True)

    content = format_calendar(events, region, year, month)
    filename = f"{year}-{month:02d}_{region}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath
