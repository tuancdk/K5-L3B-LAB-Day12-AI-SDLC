"""Ghi JSONL tất định: tọa độ làm tròn 3 chữ số; fresh giữ nguyên theo contract v1.2."""

import json


def _clean(v, field=None):
    if isinstance(v, float):
        r = v if field == "fresh" else round(v, 3)
        return 0.0 if r == 0 else r  # tránh -0.0
    if isinstance(v, dict):
        return {k: _clean(x, k) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


def dumps(obj) -> str:
    return json.dumps(_clean(obj), ensure_ascii=False, separators=(",", ":"))


class JsonlWriter:
    def __init__(self, path: str):
        self._f = open(path, "w", encoding="utf-8", newline="\n")

    def write(self, obj):
        self._f.write(dumps(obj) + "\n")

    def close(self):
        self._f.close()
