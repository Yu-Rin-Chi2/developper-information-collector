"""イベントの地域分類モジュール"""

# 関東・関西以外の都道府県名（これらが含まれていたら「その他」に分類）
_OTHER_PREFECTURES = [
    "北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島",
    "新潟", "富山", "石川", "福井", "山梨", "長野",
    "岐阜", "静岡", "愛知", "三重",
    "鳥取", "島根", "岡山", "広島", "山口",
    "徳島", "香川", "愛媛", "高知",
    "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄",
]

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
        "梅田", "難波", "なんば", "心斎橋", "天王寺", "三宮",
        "茨木", "堺", "高槻", "枚方", "吹田", "豊中", "東大阪",
        "尼崎", "西宮", "姫路", "四条", "河原町",
        "浪速",
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

    # 優先度0: 関東・関西以外の都道府県が含まれていたら即「その他」
    # （「中央区」「北区」等の曖昧な区名での誤判定を防ぐ）
    for pref in _OTHER_PREFECTURES:
        if pref in address:
            return None

    # 優先度1: 都道府県名で判定
    for region_key, keywords in _PRIMARY_KEYWORDS.items():
        for kw in keywords:
            if kw in address:
                return region_key

    # 優先度2: 区名・エリア名で判定（優先度0・1で決まらなかった場合のみ）
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
