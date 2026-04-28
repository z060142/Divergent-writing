from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any


STATUSES = {"gray", "red", "yellow", "green"}
STAGES = {"keyword", "expanded", "draft", "final"}


@dataclass
class Fragment:
    id: str
    zone: str
    stage: str
    content: str
    next_hook: str
    status: str
    grid: list[int]
    links: list[str] = field(default_factory=list)


class StateStore:
    def __init__(self, path: str = "state.json") -> None:
        self.path = Path(path)
        if not self.path.exists():
            self.init_state()

    def init_state(self) -> None:
        grid = {
            f"{x},{y}": {"status": "gray", "fragment_ids": [], "summary": ""}
            for x in range(10)
            for y in range(10)
        }
        payload = {"fragments": {}, "grid": grid, "lore": {}, "todos": []}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_fragment(self, text: str, grid: tuple[int, int], zone: str = "catcher") -> Fragment:
        data = self.load()
        frag = Fragment(
            id=str(uuid.uuid4()),
            zone=zone,
            stage="keyword",
            content=text.strip(),
            next_hook="",
            status="gray",
            grid=[grid[0], grid[1]],
        )
        data["fragments"][frag.id] = asdict(frag)
        key = f"{grid[0]},{grid[1]}"
        data["grid"][key]["fragment_ids"].append(frag.id)
        self.save(data)
        return frag
