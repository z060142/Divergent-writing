# 修補工作紀錄（Fix Session）

此文件記錄本次針對 `codex/implement-ai-driven-writing-environment` 骨架的審閱結論與修補動作，
供後續維護者理解每個改動的原因。

---

## 審閱摘要

Codex 實作的骨架方向正確——資料模型、工具合約、agent 分工的哲學都符合原始設計。
但存在四個根本性缺陷，以及多個缺失功能，必須修補後才能正常使用。

---

## 根本性缺陷（必修）

### BUG-1：防腦補檢查對中文完全無效

**位置**：`app/tools.py` → `_proper_nouns()`

**問題**：
```python
return re.findall(r"[A-Z][A-Za-z0-9_]*", text)
```
此 regex 只偵測英文大寫開頭 token。中文設定詞（角色名、地名、術語）一個都抓不到，
等於防腦補機制是空殼。

**修法**：
改為「Lore 資料庫反查」策略——
不嘗試從文字猜測哪些是專有名詞（中文 NLP 問題），
而是把 lore 資料庫中所有的 key 當作已知設定詞，
若 expansion 中出現了某個 lore key 但 `lore_refs` 沒有列出它，就標紅。
同時保留英文大寫偵測作為輔助。

**影響**：`tools.py` → `expand_fragment()` 與 `_proper_nouns()` 重寫。

---

### BUG-2：Agent 只跑單輪 tool call，流程無法完整執行

**位置**：`app/orchestrator.py` → `run()`

**問題**：
`expander_agent` 按設計需要：
1. 呼叫 `query_lore` 查詢設定
2. 拿到結果後再呼叫 `expand_fragment`

但 `run()` 只做一次「送出 → 接收 → 執行 tool」，
tool result 沒有被送回模型做第二輪推理，
整個 expand 流程實際上無法完成預期行為。

**修法**：
加入最多 `max_turns`（預設 6）輪的迴圈：
每輪把 tool results 以 `role: tool` messages 附回，
直到模型不再回傳 `tool_calls` 或達到上限為止。

**影響**：`orchestrator.py` → `run()` 重寫。

---

### BUG-3：`captain` 擁有全部工具，破壞 Lore 隔離邊界

**位置**：`config/agents.json` → `captain.allowed_tools`

**問題**：
captain 被授予了所有 9 個工具，包含 `upsert_lore`。
這讓 captain 可以直接發明並寫入設定，完全繞過 lore 隔離設計。

**修法**：
captain 只保留路由與管理類工具（`capture_fragment`、`set_fragment_stage`、
`set_fragment_hook`、`move_fragment`、`set_cell_status`、`link_fragments`）；
移除 `upsert_lore`、`expand_fragment`、`query_lore`。
這些由專責 agent 處理。

**影響**：`config/agents.json`。

---

### BUG-4：`check_coherence` 工具在架構文件中定義，但 `tools.py` 未實作

**位置**：`docs/architecture.md` Blueprint 模式描述 vs `app/tools.py`

**問題**：
`blueprint_agent` 被賦予 `check_coherence` 工具，
但該工具不存在，導致 blueprint_agent 無法執行首尾呼應檢查。

**修法**：
實作 `check_coherence(x1, y1, x2, y2)` 工具：
掃描指定範圍的 grid cell，
回報其中「stage 為 final/draft 但 next_hook 為空」或「fragment 無 links」的問題清單。

**影響**：`tools.py`、`config/agents.json`（blueprint_agent allowed_tools）、
`docs/architecture.md`（tool 合約更新）。

---

## 缺失功能（本次一併補齊）

### MISS-1：沒有 `todos` 查詢指令

`state.json` 中有 `todos` 陣列（由 `expand_fragment` 在偵測到未知 lore token 時寫入），
但 CLI 沒有辦法顯示它。使用者無法知道哪些片段標記了待修問題。

**修法**：新增 `python app/main.py todos` 指令。

---

### MISS-2：`next_hook` 缺乏軟性強制

Fragment 從 `keyword` 推進到 `expanded` 以上時，若 `next_hook` 為空，
系統不會有任何提示，使用者會忘記設定返回鉤子。

**修法**：
在 `set_fragment_stage()` 中，當 stage 推進至 `expanded` 或更高時，
若 `next_hook` 仍為空，自動向 `todos` 加入提示條目（軟性警告，不阻擋操作）。

---

## 本次修補不涉及的項目

以下問題已識別，列入 `docs/roadmap.md`，留待後續階段處理：

- Fragment 歷史版本（expand 覆蓋問題）
- 「今日未完成片段」開啟面板
- Session 恢復卡
- Web UI / 四窄模式介面
- Lore entry `updated_at` 時間戳
- Fragment `parent` / `entities` 欄位
- SQLite 遷移

---

## 修補後驗證方式

```bash
# 1. 確認中文 lore 偵測
python -m pytest tests/ -v

# 2. 確認 todos 指令
python app/main.py init
python app/main.py capture --text "香香走進舊庄" --x 3 --y 3
python app/main.py todos

# 3. 確認 board 仍可執行
python app/main.py board
```
