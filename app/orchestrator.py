from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.openrouter_client import OpenRouterClient
from app.tools import ToolRegistry

_DEFAULT_MAX_TURNS = 6


class Orchestrator:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        config_path: str = "config/agents.json",
        max_turns: int = _DEFAULT_MAX_TURNS,
    ) -> None:
        self.tools = tool_registry
        self.client = OpenRouterClient()
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.max_turns = max_turns

    def run(self, agent_name: str, user_text: str) -> dict[str, Any]:
        agent = self.config[agent_name]
        allowed = set(agent["allowed_tools"])
        tool_schemas = [t for t in self.tools.schema() if t["function"]["name"] in allowed]

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user", "content": user_text},
        ]

        all_tool_results: list[dict[str, Any]] = []
        final_text = ""

        for _ in range(self.max_turns):
            raw = self.client.chat(model=agent["model"], messages=messages, tools=tool_schemas)
            choice = raw["choices"][0]["message"]
            final_text = choice.get("content") or ""

            tool_calls = choice.get("tool_calls") or []
            if not tool_calls:
                break

            # append assistant turn with tool_calls to message history
            messages.append({
                "role": "assistant",
                "content": final_text,
                "tool_calls": tool_calls,
            })

            # execute each tool call and collect results
            turn_results = []
            for call in tool_calls:
                fn_name = call["function"]["name"]
                args = json.loads(call["function"].get("arguments", "{}"))
                if fn_name not in allowed:
                    result = {"ok": False, "error": f"tool not allowed: {fn_name}"}
                else:
                    result = self.tools.call(fn_name, args)
                turn_results.append({"tool": fn_name, "result": result})
                # feed result back as tool message so next turn sees it
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", fn_name),
                    "content": json.dumps(result, ensure_ascii=False),
                })

            all_tool_results.extend(turn_results)

        return {
            "agent": agent_name,
            "model": agent["model"],
            "assistant_text": final_text,
            "tool_results": all_tool_results,
            "turns": len([m for m in messages if m["role"] == "assistant"]),
        }
