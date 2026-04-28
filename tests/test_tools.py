from pathlib import Path

from app.store import StateStore
from app.tools import ToolRegistry


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
