"""File kho v1.0 (Contract G): {"items": {id: số nguyên >= 0}}.

Đọc: từ chối sai schema / id lạ / số âm (BadInput -> mã 2).
Ghi: bỏ mục bằng 0, qua file tạm cùng thư mục rồi thay thế, byte-ổn-định.
"""

import json
import math
import os
import tempfile

from .errors import BadInput
from .ids import id_key

# v1.1: thêm ca_keo (cá kèo), keo_neo (kèo nèo). Tên KINDS_P1 giữ để không vỡ import cũ.
KINDS_P1 = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung", "ca_keo", "keo_neo")


def validate_items(items, kinds=KINDS_P1):
    if not isinstance(items, dict):
        raise BadInput("items phải là object")
    out = {}
    for k, v in items.items():
        if k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k}")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise BadInput(f"số lượng không hợp lệ cho {k}: {v!r}")
        if v > 0:
            out[k] = v
    return out


def read_inventory(path: str, kinds=KINDS_P1) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    return validate_items(data["items"], kinds)


def hold_to_items(hold: list) -> dict:
    """Khoang (mảng id theo thứ tự nhặt) -> object đếm, sắp theo id nguyên liệu."""
    counts = {}
    for k in hold:
        counts[k] = counts.get(k, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def write_inventory(path: str, items: dict):
    items = {k: items[k] for k in sorted(items) if items[k] > 0}
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": items}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# --- v1.2 (TICKET-03): kho cá thể {"items": [{id, kind, fresh}]} ---------------------------------------

FRESH_UNITS = 240  # đơn vị nội bộ mỗi điểm tươi: gather -2/tick (0.5/s), quán -1/tick (0.25/s) — tính chính xác


def schema_version(contract_version) -> tuple:
    try:
        return tuple(int(p) for p in str(contract_version).split("."))
    except ValueError:
        raise BadInput(f"contract_version lạ: {contract_version!r}")


def is_item_schema(contract_version) -> bool:
    return schema_version(contract_version) >= (1, 2)


def validate_item_list(items, kinds=KINDS_P1, where="items"):
    """Mảng cá thể hợp lệ: id chuỗi khác rỗng duy nhất, kind thuộc danh mục, fresh hữu hạn trong [0, 100]."""
    if not isinstance(items, list):
        raise BadInput(f"{where} phải là mảng cá thể {{id, kind, fresh}} (schema v1.2)")
    out, seen = [], set()
    for i, it in enumerate(items):
        if not isinstance(it, dict) or set(it) != {"id", "kind", "fresh"}:
            raise BadInput(f"{where}[{i}] phải có đúng khóa id, kind, fresh")
        ident, kind, fresh = it["id"], it["kind"], it["fresh"]
        if not isinstance(ident, str) or not ident:
            raise BadInput(f"{where}[{i}].id phải là chuỗi khác rỗng")
        if ident in seen:
            raise BadInput(f"{where}: id trùng {ident}")
        seen.add(ident)
        if kind not in kinds:
            raise BadInput(f"{where}[{i}]: nguyên liệu lạ {kind!r}")
        if isinstance(fresh, bool) or not isinstance(fresh, (int, float)) or not math.isfinite(fresh) \
                or not 0 <= fresh <= 100:
            raise BadInput(f"{where}[{i}].fresh phải hữu hạn trong [0, 100]")
        out.append({"id": ident, "kind": kind, "fresh": fresh})
    return out


def read_inventory_v12(path, kinds=KINDS_P1) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    return validate_item_list(data["items"], kinds)


def read_inventory_for(path, contract_version):
    """Bên đọc chọn schema theo contract_version: v1.2 -> mảng cá thể; trước đó -> object đếm."""
    return read_inventory_v12(path) if is_item_schema(contract_version) else read_inventory(path)


def sort_items(items):
    return sorted(items, key=lambda it: id_key(it["id"]))


def write_inventory_items(path: str, items: list):
    """Ghi kho v1.2 sắp theo id, nguyên tử. float Python ghi dạng ngắn nhất đọc lại đúng giá trị."""
    payload = {"items": [{"id": it["id"], "kind": it["kind"], "fresh": it["fresh"]} for it in sort_items(items)]}
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def items_to_counts(items) -> dict:
    counts = {}
    for it in items:
        counts[it["kind"]] = counts.get(it["kind"], 0) + 1
    return {k: counts[k] for k in sorted(counts)}
