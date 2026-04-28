# Architecture: ADHD-first Spatial Writing System

## 1) Domain model

### Fragment (原子片段)
- `id`: UUID
- `zone`: `catcher|expander|blueprint|lore`
- `stage`: `keyword|expanded|draft|final`
- `content`: 文字內容
- `next_hook`: 強制返回鉤子（離開片段前必填）
- `status`: `gray|red|yellow|green`
- `grid`: `x,y` 對應 10x10
- `links`: 前後關聯片段 ID

### HeatmapCell
- `x,y`
- `fragment_ids`
- `status`
- `summary`

### LoreEntry
- `key`
- `value`
- `updated_at`

## 2) Narrow mode workflow

1. **Catcher**: 只允許 `capture_fragment`。
2. **Expander**: 允許 `expand_fragment`，但不可自行生成 lore 細節。
3. **Blueprint**: 允許 `move_fragment`、`set_cell_status`、`check_coherence`。
4. **Lore Bible**: 允許 `upsert_lore`、`query_lore`，且由工具返回資料。

## 3) Anti-hallucination protocol

- Expander agent 的 system prompt 明示：
  - 可以語法補全、語意銜接。
  - 不可新增世界觀專有名詞。
- Tool 層二次驗證：
  - `expand_fragment` 需附 `lore_refs`。
  - 若產生新專有名詞且不在 `lore_refs`，標記 `red`。
- Lore 與 Expander 通訊只能經由 `query_lore` tool。

## 4) Multi-agent roles (OpenRouter)

- `captain`: 任務分派 / 模式切換 / 工具路由。
- `catcher_agent`: 清洗輸入想法、建立 keyword 片段。
- `expander_agent`: keyword -> expanded/draft。
- `blueprint_agent`: 更新 10x10 熱力圖、檢查首尾呼應。
- `lore_agent`: 維護 lore bible，回覆可引用設定。
- `critic_agent`: 對 red/yellow 區塊提出修補任務。

每個 agent 可對應不同模型（例如：
- `captain`: `openai/gpt-4.1-mini`
- `expander_agent`: `anthropic/claude-3.7-sonnet`
- `critic_agent`: `google/gemini-2.5-pro`
）

## 5) Tool-call contract

所有 agent 只可透過以下工具改變狀態：
- `capture_fragment(text, grid)`
- `expand_fragment(fragment_id, expansion, lore_refs)`
- `set_fragment_stage(fragment_id, stage)`
- `set_fragment_hook(fragment_id, hook)`
- `move_fragment(fragment_id, grid)`
- `set_cell_status(grid, status, reason)`
- `upsert_lore(key, value)`
- `query_lore(key)`
- `link_fragments(from_id, to_id)`

## 6) Suggested deployment

- Backend: FastAPI / Flask (本原型先用 CLI)
- Storage: SQLite / Postgres（本原型先用 JSON）
- Frontend:
  - 左側 10x10 heatmap
  - 右側窄模式工作面板
  - 底部 hook quick bar

## 7) MVP roadmap

1. Week 1: state + tools + CLI（本 repo）
2. Week 2: Web UI + heatmap interaction
3. Week 3: 協同編輯 + session memory timeline
4. Week 4: 自動 red-zone 修補建議與版本比較
