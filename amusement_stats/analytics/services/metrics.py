def mean_absolute_error(actual: list[float], predicted: list[float]) -> float:
    pairs = _pairs(actual, predicted)
    if not pairs:
        return 0.0
    return round(sum(abs(a - p) for a, p in pairs) / len(pairs), 4)


def mean_squared_error(actual: list[float], predicted: list[float]) -> float:
    pairs = _pairs(actual, predicted)
    if not pairs:
        return 0.0
    return round(sum((a - p) ** 2 for a, p in pairs) / len(pairs), 4)


def r2_score(actual: list[float], predicted: list[float]) -> float:
    pairs = _pairs(actual, predicted)
    if len(pairs) < 2:
        return 0.0
    y_true = [a for a, _ in pairs]
    mean_actual = sum(y_true) / len(y_true)
    total = sum((a - mean_actual) ** 2 for a in y_true)
    if total == 0:
        return 0.0
    residual = sum((a - p) ** 2 for a, p in pairs)
    return round(1 - residual / total, 4)


def _pairs(actual: list[float], predicted: list[float]) -> list[tuple[float, float]]:
    return [(float(a), float(p)) for a, p in zip(actual, predicted)]
