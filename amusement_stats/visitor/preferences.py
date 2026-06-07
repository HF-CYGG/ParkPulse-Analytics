"""游客画像偏好标签的统一配置与清洗逻辑。"""

PREFERENCE_TAG_CHOICES = (
    "亲子",
    "刺激",
    "观光",
    "低排队",
    "热门",
    "低预算",
    "夜场",
    "拍照",
    "休闲",
    "长者友好",
)

PREFERENCE_TAG_FORM_CHOICES = [(tag, tag) for tag in PREFERENCE_TAG_CHOICES]

PREFERENCE_TAG_ALIASES = {
    "family": "亲子",
    "parent_child": "亲子",
    "thrill": "刺激",
    "view": "观光",
    "photo": "拍照",
    "low_queue": "低排队",
    "popular": "热门",
    "hot": "热门",
    "low_budget": "低预算",
    "night": "夜场",
    "leisure": "休闲",
    "senior": "长者友好",
}


def clean_preference_values(raw_values) -> str:
    cleaned = []
    for raw in raw_values:
        tag = str(raw).strip()
        if not tag:
            continue
        tag = PREFERENCE_TAG_ALIASES.get(tag.lower(), tag)
        if tag in PREFERENCE_TAG_CHOICES and tag not in cleaned:
            cleaned.append(tag)
    return ",".join(cleaned)


def clean_preference_string(value: str) -> str:
    return clean_preference_values(str(value or "").replace("，", ",").split(","))


def clean_preference_mapping(data) -> str:
    raw_values = []
    if hasattr(data, "getlist"):
        raw_values.extend(data.getlist("preference_tags"))
    else:
        value = data.get("preference_tags") if hasattr(data, "get") else None
        if isinstance(value, (list, tuple, set)):
            raw_values.extend(value)
        elif value:
            raw_values.extend(str(value).replace("，", ",").split(","))
    return clean_preference_values(raw_values)


def selected_preference_tags(value: str) -> list[str]:
    return [tag for tag in clean_preference_string(value).split(",") if tag]
