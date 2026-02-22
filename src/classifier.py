"""イベントの地域分類モジュール"""

# 優先度1: 都道府県・主要都市名（曖昧性なし）
_PRIMARY_KEYWORDS = {
    "kanto": [
        "東京", "神奈川", "千葉", "埼玉", "茨城", "栃木", "群馬",
        "横浜", "川崎", "相模原", "さいたま",
    ],
    "kansai": [
        "大阪", "京都", "兵庫", "奈良", "滋賀", "和歌山",
        "神戸",
    ],
}

# 優先度2: 区名・エリア名（他地域と重複しうるもの）
_SECONDARY_KEYWORDS = {
    "kanto": [
        "渋谷", "新宿", "品川", "港区", "千代田", "中央区", "目黒",
        "世田谷", "大田区", "杉並", "中野", "豊島", "板橋", "練馬",
        "足立", "葛飾", "江戸川", "墨田", "台東", "荒川", "北区",
        "文京", "江東",
    ],
    "kansai": [
        "梅田", "難波", "心斎橋", "天王寺", "三宮",
    ],
}


def classify_region(address: str) -> str | None:
    """住所テキストから地域を判定する。

    2段階で判定:
      1. 都道府県・主要都市名で判定（曖昧性なし）
      2. 区名・エリア名で判定（1で決まらなかった場合のみ）

    Args:
        address: 住所テキスト

    Returns:
        "kanto", "kansai", または None（判定不可・オンライン等）
    """
    if not address or address == "オンライン":
        return None

    # 優先度1: 都道府県名で判定
    for region_key, keywords in _PRIMARY_KEYWORDS.items():
        for kw in keywords:
            if kw in address:
                return region_key

    # 優先度2: 区名・エリア名で判定
    for region_key, keywords in _SECONDARY_KEYWORDS.items():
        for kw in keywords:
            if kw in address:
                return region_key

    return None


def classify_events(events: list[dict]) -> dict[str, list[dict]]:
    """イベントリストを地域別に分類する。

    Returns:
        {"kanto": [...], "kansai": [...], "other": [...]}
    """
    result = {"kanto": [], "kansai": [], "other": []}

    for event in events:
        region = classify_region(event.get("address", ""))
        if region:
            result[region].append(event)
        else:
            result["other"].append(event)

    return result
