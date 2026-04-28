from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.openrouter_client import OpenRouterClient
from app.tools import ToolRegistry


class Orchestrator:
    def __init__(self, tool_registry: ToolRegistry, config_path: str = "config/agents.json") -> None:
        self.tools = tool_registry
        self.client = OpenRouterClient()
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))

    def run(self, agent_name: str, user_text: str) -> dict[str, Any]:
        agent = self.config[agent_name]
        tool_schemas = [
            t for t in self.tools.schema() if t["function"]["name"] in set(agent["allowed_tools"])
        ]
        messages = [
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user", "content": user_text},
        ]
        raw = self.client.chat(model=agent["model"], messages=messages, tools=tool_schemas)
        choice = raw["choices"][0]["message"]

        tool_calls = choice.get("tool_calls", [])
        tool_results = []
        for call in tool_calls:
            fn_name = call["function"]["name"]
            args = json.loads(call["function"].get("arguments", "{}"))
            if fn_name not in agent["allowed_tools"]:
                tool_results.append({"ok": False, "error": f"tool not allowed: {fn_name}"})
                continue
            result = self.tools.call(fn_name, args)
            tool_results.append({"tool": fn_name, "result": result})

        return {
            "agent": agent_name,
            "model": agent["model"],
            "assistant_text": choice.get("content", ""),
            "tool_results": tool_results,
        }
