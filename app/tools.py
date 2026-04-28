from __future__ import annotations

from typing import Any

from app.store import StateStore, STAGES, STATUSES


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
        unknown_tokens = [token for token in self._proper_nouns(expansion) if token not in lore_refs]
        if unknown_tokens:
            frag["status"] = "red"
            data["todos"].append(f"Fragment {fragment_id} has unknown lore tokens: {unknown_tokens}")
        else:
            frag["status"] = "yellow"
        self.store.save(data)
        return {"ok": True, "status": frag["status"], "unknown": unknown_tokens}

    def set_fragment_stage(self, fragment_id: str, stage: str) -> dict[str, Any]:
        if stage not in STAGES:
            return {"ok": False, "error": f"invalid stage: {stage}"}
        data = self.store.load()
        data["fragments"][fragment_id]["stage"] = stage
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

    def _proper_nouns(self, text: str) -> list[str]:
        import re

        return re.findall(r"[A-Z][A-Za-z0-9_]*", text)
