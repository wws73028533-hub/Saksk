# -*- coding: utf-8 -*-
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

TAG_STORE_KEY = "question_tags_v1"
MAX_TAG_NAME_LEN = 20
MAX_TAGS_PER_USER = 200
MAX_TAGS_PER_QUESTION = 20


def _normalize_tag_name(name: Any) -> str:
    s = (name or "").strip()
    if not s:
        return ""
    s = re.sub(r"\s+", " ", str(s)).strip()
    if len(s) > MAX_TAG_NAME_LEN:
        s = s[:MAX_TAG_NAME_LEN].strip()
    return s


def _empty_store() -> Dict[str, Any]:
    return {"version": 1, "tags": [], "bindings": {}}


def load_store(conn, user_id: int) -> Dict[str, Any]:
    row = conn.execute(
        "SELECT data FROM user_progress WHERE user_id=? AND p_key=?",
        (user_id, TAG_STORE_KEY),
    ).fetchone()
    if not row:
        return _empty_store()

    try:
        data = row["data"]
    except Exception:
        data = None

    if not data:
        return _empty_store()

    try:
        raw = json.loads(data)
    except Exception:
        return _empty_store()

    if not isinstance(raw, dict):
        return _empty_store()

    tags = raw.get("tags")
    bindings = raw.get("bindings")
    store = {
        "version": 1,
        "tags": tags if isinstance(tags, list) else [],
        "bindings": bindings if isinstance(bindings, dict) else {},
    }
    return store


def save_store(conn, user_id: int, store: Dict[str, Any]) -> None:
    data_json = json.dumps(store, ensure_ascii=False)
    existing = conn.execute(
        "SELECT id FROM user_progress WHERE user_id=? AND p_key=?",
        (user_id, TAG_STORE_KEY),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE user_progress SET data=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND p_key=?",
            (data_json, user_id, TAG_STORE_KEY),
        )
    else:
        try:
            conn.execute(
                "INSERT INTO user_progress (user_id, p_key, data, updated_at, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (user_id, TAG_STORE_KEY, data_json),
            )
        except Exception:
            conn.execute(
                "INSERT INTO user_progress (user_id, p_key, data, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (user_id, TAG_STORE_KEY, data_json),
            )


def list_user_tags(conn, user_id: int) -> List[Dict[str, Any]]:
    store = load_store(conn, user_id)
    tags: List[str] = []
    for t in store.get("tags") or []:
        name = _normalize_tag_name(t)
        if name and name not in tags:
            tags.append(name)

    counts: Dict[str, int] = {name: 0 for name in tags}
    bindings = store.get("bindings") or {}
    if isinstance(bindings, dict):
        for _, tag_list in bindings.items():
            if not isinstance(tag_list, list):
                continue
            seen: Set[str] = set()
            for t in tag_list:
                name = _normalize_tag_name(t)
                if not name or name in seen:
                    continue
                seen.add(name)
                if name in counts:
                    counts[name] += 1

    return [{"name": name, "count": counts.get(name, 0)} for name in tags]


def create_user_tag(conn, user_id: int, name: Any) -> Tuple[bool, str, str]:
    tag = _normalize_tag_name(name)
    if not tag:
        return False, "标签名不能为空", ""
    if tag.lower() == "all":
        return False, "标签名不可用", ""

    store = load_store(conn, user_id)
    tags = store.get("tags") if isinstance(store.get("tags"), list) else []
    normalized = [_normalize_tag_name(x) for x in tags]
    normalized = [x for x in normalized if x]

    if tag in normalized:
        return True, "已存在", tag

    if len(normalized) >= MAX_TAGS_PER_USER:
        return False, f"标签数量已达上限（{MAX_TAGS_PER_USER}）", ""

    normalized.append(tag)
    store["tags"] = normalized
    save_store(conn, user_id, store)
    return True, "已创建", tag


def delete_user_tag(conn, user_id: int, name: Any) -> Tuple[bool, str]:
    tag = _normalize_tag_name(name)
    if not tag:
        return False, "标签名不能为空"

    store = load_store(conn, user_id)
    tags = store.get("tags") if isinstance(store.get("tags"), list) else []
    tags_norm = [_normalize_tag_name(x) for x in tags]
    tags_norm = [x for x in tags_norm if x and x != tag]
    store["tags"] = tags_norm

    bindings = store.get("bindings")
    if isinstance(bindings, dict):
        next_bindings: Dict[str, Any] = {}
        for qid, tag_list in bindings.items():
            if not isinstance(tag_list, list):
                continue
            kept = []
            for t in tag_list:
                tn = _normalize_tag_name(t)
                if tn and tn != tag and tn not in kept:
                    kept.append(tn)
            if kept:
                next_bindings[str(qid)] = kept
        store["bindings"] = next_bindings
    else:
        store["bindings"] = {}

    save_store(conn, user_id, store)
    return True, "已删除"


def get_question_tags(conn, user_id: int, question_id: int) -> List[str]:
    store = load_store(conn, user_id)
    bindings = store.get("bindings") or {}
    if not isinstance(bindings, dict):
        return []
    raw = bindings.get(str(question_id))
    if not isinstance(raw, list):
        return []
    tags: List[str] = []
    for t in raw:
        name = _normalize_tag_name(t)
        if name and name not in tags:
            tags.append(name)
    return tags


def set_question_tags(conn, user_id: int, question_id: int, tags: Any) -> Tuple[bool, str, List[str]]:
    if tags is None:
        tags_list: List[Any] = []
    elif isinstance(tags, list):
        tags_list = tags
    else:
        tags_list = [tags]

    normalized: List[str] = []
    for t in tags_list:
        name = _normalize_tag_name(t)
        if not name:
            continue
        if name.lower() == "all":
            continue
        if name not in normalized:
            normalized.append(name)
        if len(normalized) >= MAX_TAGS_PER_QUESTION:
            break

    store = load_store(conn, user_id)
    tags_list = store.get("tags") if isinstance(store.get("tags"), list) else []
    tags_norm = [_normalize_tag_name(x) for x in tags_list]
    tags_norm = [x for x in tags_norm if x]

    # 确保标签存在于 tags 列表（避免调用 create_user_tag 后被本次 save 覆盖）
    existing = set(tags_norm)
    for name in normalized:
        if name in existing:
            continue
        if len(tags_norm) >= MAX_TAGS_PER_USER:
            return False, f"标签数量已达上限（{MAX_TAGS_PER_USER}）", get_question_tags(conn, user_id, question_id)
        tags_norm.append(name)
        existing.add(name)
    store["tags"] = tags_norm

    bindings = store.get("bindings")
    if not isinstance(bindings, dict):
        bindings = {}

    if normalized:
        bindings[str(question_id)] = normalized
    else:
        bindings.pop(str(question_id), None)

    store["bindings"] = bindings
    save_store(conn, user_id, store)
    return True, "已更新", normalized


def update_question_tags(
    conn,
    user_id: int,
    question_id: int,
    *,
    add: Optional[Any] = None,
    remove: Optional[Any] = None,
) -> Tuple[bool, str, List[str]]:
    cur = get_question_tags(conn, user_id, question_id)
    cur_set = list(cur)

    add_list: List[Any] = []
    if add is not None:
        add_list = add if isinstance(add, list) else [add]

    remove_list: List[Any] = []
    if remove is not None:
        remove_list = remove if isinstance(remove, list) else [remove]

    to_add: List[str] = []
    for t in add_list:
        name = _normalize_tag_name(t)
        if name and name not in cur_set and name.lower() != "all":
            to_add.append(name)

    to_remove: Set[str] = set()
    for t in remove_list:
        name = _normalize_tag_name(t)
        if name:
            to_remove.add(name)

    next_tags: List[str] = []
    for name in cur_set:
        if name in to_remove:
            continue
        next_tags.append(name)
    for name in to_add:
        if name not in next_tags:
            next_tags.append(name)

    if len(next_tags) > MAX_TAGS_PER_QUESTION:
        next_tags = next_tags[:MAX_TAGS_PER_QUESTION]

    ok, msg, updated = set_question_tags(conn, user_id, question_id, next_tags)
    return ok, msg, updated


def get_question_ids_by_tag(conn, user_id: int, tag_name: Any) -> Set[int]:
    tag = _normalize_tag_name(tag_name)
    if not tag:
        return set()
    store = load_store(conn, user_id)
    bindings = store.get("bindings") or {}
    if not isinstance(bindings, dict):
        return set()
    ids: Set[int] = set()
    for qid, tag_list in bindings.items():
        if not isinstance(tag_list, list):
            continue
        for t in tag_list:
            if _normalize_tag_name(t) == tag:
                try:
                    ids.add(int(qid))
                except Exception:
                    pass
                break
    return ids
