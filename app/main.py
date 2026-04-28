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
    sub.add_parser("todos")

    p_coherence = sub.add_parser("coherence")
    p_coherence.add_argument("--x1", type=int, default=0)
    p_coherence.add_argument("--y1", type=int, default=0)
    p_coherence.add_argument("--x2", type=int, default=9)
    p_coherence.add_argument("--y2", type=int, default=9)

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
            "Call query_lore for any setting details you need, then call expand_fragment "
            "(list all lore keys you used in lore_refs), then call set_fragment_hook."
        )
        result = orch.run("expander_agent", prompt)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.cmd == "board":
        data = store.load()
        print("     " + "".join(f"{x:<2}" for x in range(10)))
        for y in range(10):
            row = []
            for x in range(10):
                s = data["grid"][f"{x},{y}"]["status"]
                ch = {"gray": "⬜", "red": "🟥", "yellow": "🟨", "green": "🟩"}[s]
                row.append(ch)
            print(f"  {y:<2} " + "".join(row))
        return

    if args.cmd == "todos":
        data = store.load()
        todos = data.get("todos", [])
        if not todos:
            print("✓ 沒有待處理項目")
        else:
            print(f"待處理項目（{len(todos)} 筆）：\n")
            for i, item in enumerate(todos, 1):
                print(f"  {i:>2}. {item}")
        return

    if args.cmd == "coherence":
        result = tools.check_coherence(args.x1, args.y1, args.x2, args.y2)
        if not result["issues"]:
            print(f"✓ 範圍 ({args.x1},{args.y1})→({args.x2},{args.y2}) 無首尾呼應問題")
        else:
            print(f"發現 {result['count']} 個問題：\n")
            for issue in result["issues"]:
                print(f"  • {issue}")
        return


if __name__ == "__main__":
    cli()
