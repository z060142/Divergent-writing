from __future__ import annotations

import re
from typing import Any

from app.store import StateStore, STAGES, STATUSES

_STAGES_NEEDING_HOOK = {"expanded", "draft", "final"}


class ToolRegistry:
    def __init__(self, store: StateStore) -> None:
        self.store = store

    def schema(self) -> list[dict[str, Any]]:
        return [
            self._fn("capture_fragment", {"text": "string", "x": "integer", "y": "integer"}),
            self._fn("expand_fragment", {"fragment_id": "string", "expansion": "string", "lore_refs": "array"}),
            self._fn("set_fragment_stage", {"fragment_id": "string", "stage": "string"}),
            self._fn("set_fragment_hook", {"fragment_id": "string", "hook": "string"}),
            self._fn("move_fragment", {"fragment_id": "string", "x": "integer", "y": "integer"}),
            self._fn("set_cell_status", {"x": "integer", "y": "integer", "status": "string", "reason": "string"}),
            self._fn("upsert_lore", {"key": "string", "value": "string"}),
            self._fn("query_lore", {"key": "string"}),
            self._fn("link_fragments", {"from_id": "string", "to_id": "string"}),
            self._fn("check_coherence", {"x1": "integer", "y1": "integer", "x2": "integer", "y2": "integer"}),
        ]

    def _fn(self, name: str, props: dict[str, str]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": name,
                "parameters": {
                    "type": "object",
                    "properties": {k: {"type": v} for k, v in props.items()},
                    "required": list(props.keys()),
                },
            },
        }

    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        fn = getattr(self, name)
        return fn(**args)

    def capture_fragment(self, text: str, x: int, y: int) -> dict[str, Any]:
        frag = self.store.create_fragment(text=text, grid=(x, y), zone="catcher")
        return {"ok": True, "fragment_id": frag.id}

    def expand_fragment(self, fragment_id: str, expansion: str, lore_refs: list[str]) -> dict[str, Any]:
        data = self.store.load()
        frag = data["fragments"][fragment_id]
        frag["content"] = expansion
        frag["stage"] = "expanded"

        unknown_tokens = self._detect_undeclared_lore(expansion, lore_refs, data["lore"])
        if unknown_tokens:
            frag["status"] = "red"
            data["todos"].append(
                f"Fragment {fragment_id[:8]} 使用了未在 lore_refs 聲明的設定詞: {unknown_tokens}"
            )
        else:
            frag["status"] = "yellow"

        # 軟性提示：推進至 expanded 但 next_hook 為空
        if not frag.get("next_hook"):
            data["todos"].append(
                f"Fragment {fragment_id[:8]} 已擴寫但尚未設定返回鉤子（next_hook 為空）"
            )

        self.store.save(data)
        return {"ok": True, "status": frag["status"], "unknown": unknown_tokens}

    def set_fragment_stage(self, fragment_id: str, stage: str) -> dict[str, Any]:
        if stage not in STAGES:
            return {"ok": False, "error": f"invalid stage: {stage}"}
        data = self.store.load()
        frag = data["fragments"][fragment_id]
        frag["stage"] = stage
        # 軟性提示：推進至需要鉤子的 stage 但 next_hook 為空
        if stage in _STAGES_NEEDING_HOOK and not frag.get("next_hook"):
            data["todos"].append(
                f"Fragment {fragment_id[:8]} 推進至 {stage} 但尚未設定返回鉤子（next_hook 為空）"
            )
        self.store.save(data)
        return {"ok": True}

    def set_fragment_hook(self, fragment_id: str, hook: str) -> dict[str, Any]:
        data = self.store.load()
        data["fragments"][fragment_id]["next_hook"] = hook
        self.store.save(data)
        return {"ok": True}

    def move_fragment(self, fragment_id: str, x: int, y: int) -> dict[str, Any]:
        data = self.store.load()
        frag = data["fragments"][fragment_id]
        old_key = f"{frag['grid'][0]},{frag['grid'][1]}"
        new_key = f"{x},{y}"
        if fragment_id in data["grid"][old_key]["fragment_ids"]:
            data["grid"][old_key]["fragment_ids"].remove(fragment_id)
        data["grid"][new_key]["fragment_ids"].append(fragment_id)
        frag["grid"] = [x, y]
        self.store.save(data)
        return {"ok": True}

    def set_cell_status(self, x: int, y: int, status: str, reason: str) -> dict[str, Any]:
        if status not in STATUSES:
            return {"ok": False, "error": f"invalid status: {status}"}
        data = self.store.load()
        key = f"{x},{y}"
        data["grid"][key]["status"] = status
        data["grid"][key]["summary"] = reason
        self.store.save(data)
        return {"ok": True}

    def upsert_lore(self, key: str, value: str) -> dict[str, Any]:
        data = self.store.load()
        data["lore"][key] = value
        self.store.save(data)
        return {"ok": True}

    def query_lore(self, key: str) -> dict[str, Any]:
        data = self.store.load()
        return {"ok": True, "value": data["lore"].get(key, "")}

    def link_fragments(self, from_id: str, to_id: str) -> dict[str, Any]:
        data = self.store.load()
        links = data["fragments"][from_id].setdefault("links", [])
        if to_id not in links:
            links.append(to_id)
        self.store.save(data)
        return {"ok": True}

    def check_coherence(self, x1: int, y1: int, x2: int, y2: int) -> dict[str, Any]:
        """掃描 grid 矩形範圍內的片段，回報首尾呼應問題。"""
        data = self.store.load()
        issues: list[str] = []

        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                cell = data["grid"].get(f"{x},{y}", {})
                for fid in cell.get("fragment_ids", []):
                    frag = data["fragments"].get(fid)
                    if not frag:
                        continue
                    stage = frag.get("stage", "keyword")
                    hook = frag.get("next_hook", "")
                    links = frag.get("links", [])
                    short = fid[:8]
                    if stage in _STAGES_NEEDING_HOOK and not hook:
                        issues.append(f"({x},{y}) Fragment {short} [{stage}] 缺少返回鉤子")
                    if stage in {"draft", "final"} and not links:
                        issues.append(f"({x},{y}) Fragment {short} [{stage}] 無連結，可能是孤立片段")

        return {"ok": True, "issues": issues, "count": len(issues)}

    def _detect_undeclared_lore(
        self, text: str, lore_refs: list[str], lore_db: dict[str, Any]
    ) -> list[str]:
        """
        回傳出現在 text 中、但未在 lore_refs 聲明的設定詞。

        策略（同時支援中英文）：
        1. 從 lore 資料庫反查：若任何 lore key 出現在 text 中，視為使用了該設定詞。
           若未列在 lore_refs，標為未聲明。
        2. 英文輔助：偵測大寫開頭 token，若不在 lore_refs 也不在 lore_db，視為新造詞彙。
        """
        undeclared: list[str] = []

        # 策略 1：lore 資料庫反查（支援中英文）
        for key in lore_db:
            if key in text and key not in lore_refs:
                undeclared.append(key)

        # 策略 2：英文大寫 token 輔助偵測
        en_tokens = re.findall(r"[A-Z][A-Za-z0-9_]*", text)
        for token in en_tokens:
            if token not in lore_refs and token not in lore_db and token not in undeclared:
                undeclared.append(token)

        return undeclared
