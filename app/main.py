from __future__ import annotations

import argparse
import json

from app.orchestrator import Orchestrator
from app.store import StateStore
from app.tools import ToolRegistry


def cli() -> None:
    parser = argparse.ArgumentParser(description="Divergent Writing Engine CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    p_capture = sub.add_parser("capture")
    p_capture.add_argument("--text", required=True)
    p_capture.add_argument("--x", type=int, default=0)
    p_capture.add_argument("--y", type=int, default=0)

    p_expand = sub.add_parser("expand")
    p_expand.add_argument("--fragment-id", required=True)

    sub.add_parser("board")

    args = parser.parse_args()
    store = StateStore()
    tools = ToolRegistry(store)

    if args.cmd == "init":
        store.init_state()
        print("initialized state.json")
        return

    if args.cmd == "capture":
        result = tools.capture_fragment(args.text, args.x, args.y)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.cmd == "expand":
        orch = Orchestrator(tools)
        prompt = (
            "Expand this fragment into clear prose. "
            f"fragment_id={args.fragment_id}. "
            "Call query_lore if needed, then call expand_fragment and set_fragment_hook."
        )
        result = orch.run("expander_agent", prompt)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.cmd == "board":
        data = store.load()
        for y in range(10):
            row = []
            for x in range(10):
                s = data["grid"][f"{x},{y}"]["status"]
                ch = {"gray": "⬜", "red": "🟥", "yellow": "🟨", "green": "🟩"}[s]
                row.append(ch)
            print("".join(row))
        return


if __name__ == "__main__":
    cli()
