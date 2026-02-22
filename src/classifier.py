"""イベントの地域分類モジュール"""

REGIONS = {
    "kanto": {
        "label": "関東",
        "prefectures": [
            "東京", "神奈川", "千葉", "埼玉", "茨城", "栃木", "群馬",
            # 住所表記のゆれに対応
            "渋谷", "新宿", "品川", "港区", "千代田", "中央区", "目黒",
            "世田谷", "大田区", "杉並", "中野", "豊島", "板橋", "練馬",
            "足立", "葛飾", "江戸川", "墨田", "台東", "荒川", "北区",
            "文京", "江東", "横浜", "川崎", "相模原", "さいたま",
        ],
    },
    "kansai": {
        "label": "関西",
        "prefectures": [
            "大阪", "京都", "兵庫", "奈良", "滋賀", "和歌山",
            "梅田", "難波", "心斎橋", "天王寺", "神戸", "三宮",
        ],
    },
}


def classify_region(address: str) -> str | None:
    """住所テキストから地域を判定する。

    Args:
        address: 住所テキスト

    Returns:
        "kanto", "kansai", または None（判定不可・オンライン等）
    """
    if not address or address == "オンライン":
        return None

    for region_key, region_data in REGIONS.items():
        for keyword in region_data["prefectures"]:
            if keyword in address:
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
