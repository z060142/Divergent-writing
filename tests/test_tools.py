from pathlib import Path

import pytest

from app.store import StateStore
from app.tools import ToolRegistry


@pytest.fixture
def tools(tmp_path: Path) -> ToolRegistry:
    store = StateStore(path=str(tmp_path / "state.json"))
    return ToolRegistry(store)


# ── BUG-1 修補驗證：中文 lore 偵測 ───────────────────────────────────────────

def test_chinese_lore_detection_flags_undeclared(tools: ToolRegistry) -> None:
    """中文 lore key 出現在 expansion 但未在 lore_refs 中，應標紅。"""
    tools.upsert_lore("香香", "廟祝之女，國三，無陰陽眼")
    created = tools.capture_fragment("女主角進入舊庄", 1, 1)
    fid = created["fragment_id"]

    result = tools.expand_fragment(fid, "女主角走進舊庄，遇見了香香。", lore_refs=[])
    assert result["status"] == "red"
    assert "香香" in result["unknown"]


def test_chinese_lore_detection_passes_when_declared(tools: ToolRegistry) -> None:
    """中文 lore key 出現在 expansion 且已在 lore_refs 中，應標黃（非紅）。"""
    tools.upsert_lore("香香", "廟祝之女，國三，無陰陽眼")
    created = tools.capture_fragment("女主角進入舊庄", 2, 2)
    fid = created["fragment_id"]

    result = tools.expand_fragment(fid, "女主角走進舊庄，遇見了香香。", lore_refs=["香香"])
    assert result["status"] == "yellow"
    assert result["unknown"] == []


def test_english_token_detection_still_works(tools: ToolRegistry) -> None:
    """英文大寫 token 未在 lore_refs 且未在 lore_db，應標紅（向下相容）。"""
    created = tools.capture_fragment("夜色降臨", 1, 2)
    fid = created["fragment_id"]

    result = tools.expand_fragment(fid, "夜色降臨，主角走進OldTown。", lore_refs=[])
    assert result["status"] == "red"
    assert "OldTown" in result["unknown"]


def test_english_token_passes_when_in_lore(tools: ToolRegistry) -> None:
    """英文 token 已在 lore_db 中，不應標記為未知。"""
    tools.upsert_lore("OldTown", "舊城區")
    created = tools.capture_fragment("夜色降臨", 3, 3)
    fid = created["fragment_id"]

    result = tools.expand_fragment(fid, "夜色降臨，主角走進OldTown。", lore_refs=["OldTown"])
    assert result["status"] == "yellow"


# ── MISS-2 修補驗證：next_hook 軟性提示 ──────────────────────────────────────

def test_expand_without_hook_writes_todo(tools: ToolRegistry) -> None:
    """expand 後若 next_hook 為空，應在 todos 中留下提示。"""
    created = tools.capture_fragment("主角獨自思考", 0, 0)
    fid = created["fragment_id"]

    tools.expand_fragment(fid, "主角獨自坐在窗邊思考。", lore_refs=[])
    data = tools.store.load()
    hook_todos = [t for t in data["todos"] if "返回鉤子" in t and fid[:8] in t]
    assert len(hook_todos) >= 1


def test_expand_with_hook_does_not_warn(tools: ToolRegistry) -> None:
    """expand 前先設定 hook，expand 後不應產生 hook 提示。"""
    created = tools.capture_fragment("主角獨自思考", 0, 1)
    fid = created["fragment_id"]
    tools.set_fragment_hook(fid, "下一步：補充對白")

    tools.expand_fragment(fid, "主角獨自坐在窗邊思考。", lore_refs=[])
    data = tools.store.load()
    hook_todos = [t for t in data["todos"] if "返回鉤子" in t and fid[:8] in t]
    assert len(hook_todos) == 0


def test_set_stage_without_hook_writes_todo(tools: ToolRegistry) -> None:
    """推進 stage 至 draft 時若 next_hook 為空，應寫入 todo。"""
    created = tools.capture_fragment("對白場景", 5, 5)
    fid = created["fragment_id"]

    tools.set_fragment_stage(fid, "draft")
    data = tools.store.load()
    hook_todos = [t for t in data["todos"] if "返回鉤子" in t and fid[:8] in t]
    assert len(hook_todos) >= 1


# ── BUG-4 修補驗證：check_coherence ──────────────────────────────────────────

def test_check_coherence_detects_missing_hook(tools: ToolRegistry) -> None:
    """draft 片段沒有 next_hook，check_coherence 應回報問題。"""
    created = tools.capture_fragment("場景片段", 2, 3)
    fid = created["fragment_id"]
    tools.set_fragment_stage(fid, "draft")

    result = tools.check_coherence(0, 0, 9, 9)
    assert result["ok"] is True
    assert result["count"] >= 1
    issue_text = " ".join(result["issues"])
    assert fid[:8] in issue_text


def test_check_coherence_detects_isolated_final(tools: ToolRegistry) -> None:
    """final 片段無 links，check_coherence 應回報孤立片段問題。"""
    created = tools.capture_fragment("結尾場景", 7, 7)
    fid = created["fragment_id"]
    tools.set_fragment_stage(fid, "final")

    result = tools.check_coherence(5, 5, 9, 9)
    assert result["count"] >= 1
    issue_text = " ".join(result["issues"])
    assert fid[:8] in issue_text


def test_check_coherence_clean_when_linked_and_hooked(tools: ToolRegistry) -> None:
    """已設 hook 且已連結的 final 片段，check_coherence 不應回報問題。"""
    a = tools.capture_fragment("場景A", 1, 0)
    b = tools.capture_fragment("場景B", 2, 0)
    fid_a = a["fragment_id"]
    fid_b = b["fragment_id"]

    tools.set_fragment_hook(fid_a, "進入場景B")
    tools.set_fragment_stage(fid_a, "final")
    tools.link_fragments(fid_a, fid_b)

    result = tools.check_coherence(1, 0, 2, 0)
    issue_text = " ".join(result["issues"])
    assert fid_a[:8] not in issue_text


# ── 原始 lifecycle 測試（保留向下相容）───────────────────────────────────────

def test_fragment_lifecycle(tmp_path: Path) -> None:
    store = StateStore(path=str(tmp_path / "state.json"))
    tools = ToolRegistry(store)

    created = tools.capture_fragment("夜色降臨", 1, 2)
    fid = created["fragment_id"]

    expanded = tools.expand_fragment(fid, "夜色降臨，主角走進OldTown。", lore_refs=[])
    assert expanded["status"] == "red"

    tools.upsert_lore("OldTown", "舊城區")
    expanded2 = tools.expand_fragment(fid, "夜色降臨，主角走進OldTown。", lore_refs=["OldTown"])
    assert expanded2["status"] == "yellow"

    hook = tools.set_fragment_hook(fid, "下一段：反派破門")
    assert hook["ok"] is True
