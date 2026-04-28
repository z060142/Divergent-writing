# 完整路線圖（Roadmap）

這份文件描述把「現有骨架」推進到「可實際使用的 ADHD 寫作作業系統」所需的全部工作，
按優先序分為五個階段。

---

## 現狀快照（Phase 0，已完成）

Codex 實作了可執行的 Python CLI 骨架：

| 已有 | 說明 |
|---|---|
| Fragment 資料模型 | id / stage / content / next_hook / status / grid / links |
| 10x10 熱力圖 | HeatmapCell，四色燈號（gray/red/yellow/green） |
| 9 個工具函式 | capture / expand / stage / hook / move / cell_status / lore upsert / lore query / link |
| Multi-agent 架構 | 6 個 agent，各有不同模型與工具權限 |
| OpenRouter 整合 | 支援跨供應商模型（GPT / Claude / Gemini） |
| CLI 入口 | init / capture / expand / board |
| 基礎測試 | fragment lifecycle 測試 |

---

## Phase 1：修補根本性缺陷（本次 PR）

目標：讓骨架在中文環境下可以正確運作。

| 項目 | 說明 |
|---|---|
| BUG-1：中文 lore 偵測 | 改為 lore 資料庫反查策略，支援繁體中文設定詞 |
| BUG-2：多輪 tool call | Orchestrator 加入最多 6 輪迴圈，支援 query → expand 兩步流程 |
| BUG-3：captain 權限 | 移除 captain 的 upsert_lore，強化 lore 邊界 |
| BUG-4：check_coherence | 實作工具，掃描 grid 範圍回報首尾呼應問題 |
| MISS-1：todos 指令 | CLI 新增 todos 子命令 |
| MISS-2：next_hook 提示 | stage 推進時若 hook 為空自動寫入 todo |

---

## Phase 2：資料模型補完

目標：讓 Fragment 能夠完整承載寫作中途資訊，支援後續 UI 需求。

### 2-1 Fragment 擴充欄位

| 欄位 | 類型 | 用途 |
|---|---|---|
| `parent` | fragment_id \| null | 記錄此片段從哪個片段演化（版本樹） |
| `entities` | list[string] | 明確引用的 lore key（支援設定提示面板） |
| `zone` | enum 可變更 | 允許透過工具切換 catcher/expander/blueprint/lore |
| `history` | list[{ts, content}] | expand 覆蓋前保留舊內容（最多 5 版） |

### 2-2 Lore entry 補完

| 欄位 | 用途 |
|---|---|
| `updated_at` | ISO 時間戳，顯示設定最後修改時間 |
| `status` | confirmed / inferred / pending / deprecated |
| `source_fragment_ids` | 溯源：這條設定從哪幾個原始片段推導出來 |
| `forbidden_extensions` | 「不可擅自延伸」清單，查詢時一併顯示 |

### 2-3 SectionAnchor（命名位置）

```
SectionAnchor {
  id, title,
  grid_range: {x1,y1,x2,y2},
  intended_order: int
}
```

Fragment 可以有 `anchor_id` 指向命名段落（例如「第一章 舊庄初遇」），
讓 blueprint_agent 在排序時有語意依據，不只靠座標。

### 2-2 工具新增

| 工具 | 說明 |
|---|---|
| `upsert_anchor(id, title, grid_range, order)` | 建立或更新命名段落 |
| `list_anchors()` | 列出所有段落及其 grid 範圍 |
| `get_fragment_history(fragment_id)` | 取得片段歷史版本 |
| `set_fragment_entities(fragment_id, entity_keys)` | 更新片段引用的 lore key |

---

## Phase 3：ADHD UX 核心功能

目標：實作真正幫助注意力管理的畫面邏輯，讓每次開啟系統都知道「繼續做什麼」。

### 3-1 Session 恢復卡

每次結束工作時，系統自動產生一份 `session_snapshot.json`：

```json
{
  "last_active_fragment": "...",
  "last_active_anchor": "第一章 舊庄初遇",
  "in_progress_fragments": ["..."],
  "pending_todos": 3,
  "resume_hint": "下一步：把香香的第一段對白寫成粗稿"
}
```

CLI 新增 `python app/main.py resume` 指令，讀取並顯示這份快照。

### 3-2 未完成片段面板

`python app/main.py unfinished` 指令：

- 顯示最近 24 小時內編輯過、且 stage 仍為 keyword 或 expanded 的片段
- 顯示所有 status 為 red 的片段
- 每個片段一行：`[ID-前8碼] [stage] [grid位置] [內容前30字] [next_hook]`

### 3-3 當前工作卡（Context Card）

在撰寫模式中，固定顯示一張卡片，包含：

- 當前片段的 stage、所屬 anchor
- 本段「不可違反設定」（從 entities 連結的 lore forbidden_extensions）
- 相鄰 grid cell 的 polished/final 片段摘要（前後文感知）
- 下一個最小動作（next_hook）

MVP 實作：CLI `python app/main.py context --fragment-id <id>` 指令。

### 3-4 返回鉤子強制工作流

從 Phase 1 的軟性提示升級為：

- `expand_fragment` 呼叫後，若 `next_hook` 仍為空，回傳 `warning: hook_missing`
- `set_fragment_stage` 推進至 `draft` 或 `final` 時，若 `next_hook` 為空，拒絕推進並回傳錯誤

---

## Phase 4：Web UI

目標：把 CLI 功能包裝成可互動的網頁介面，讓四個窄模式有對應的視覺呈現。

### 技術選型建議

| 層 | 建議 |
|---|---|
| Backend | FastAPI + SQLite（從 JSON store 遷移） |
| Frontend | React 或 Vue3，搭配 shadcn/ui |
| 部署 | 本機 localhost，不需雲端 |

### 4-1 十乘十熱力圖

- 左側固定顯示 10x10 grid，每格顯示燈號顏色
- 點擊格子顯示該格的 fragment 清單與摘要
- 拖拉片段到不同格子（`move_fragment`）
- 圈選矩形範圍後自動呼叫 `check_coherence`

### 4-2 四個窄模式面板（右側切換）

| 模式 | 主要操作 |
|---|---|
| **捕獲模式** | 純文字輸入，每行一個片段，Enter 送出即 `capture_fragment`，零摩擦 |
| **整理模式** | 看板視圖，每欄一個 anchor，可拖拉片段、改 stage、設 entities |
| **撰寫模式** | 選定 anchor 後只顯示此 anchor 的片段＋相鄰 anchor 的 final 片段；四層寫作（keyword/expanded/draft/final）並排 |
| **校稿模式** | 依 anchor 順序串接所有 final 片段，唯讀預覽；可標記連貫性問題（寫入 todo），不能直接改字 |

### 4-3 底部快速 Hook Bar

固定顯示最近 5 個 next_hook 的片段，一鍵跳回繼續工作。

### 4-4 SQLite 遷移

- 保留 JSON store 作為開發/測試環境
- 新增 `app/db.py`，以 SQLAlchemy 實作相同介面
- 透過環境變數 `STORE_BACKEND=sqlite|json` 切換

---

## Phase 5：進階功能

### 5-1 一致性自動檢查

`critic_agent` 定期掃描（或手動觸發），檢查：

- 角色能力是否前後矛盾（例如某處說「無陰陽眼」，後文卻描述「看見鬼神」）
- 同一 lore key 在不同片段的描述是否一致
- 伏筆承諾是否有回收（anchor 標記的「埋下承諾」是否對應到後段 anchor 的「回收位置」）

### 5-2 版本比較

`get_fragment_history` 基礎上，加入 diff 顯示：
在撰寫模式中可以看到 keyword → expanded → draft → final 各版本的文字差異。

### 5-3 匯出

- `python app/main.py export --anchor <anchor_id>` 按 anchor 順序輸出 final 片段為 Markdown 或純文字
- 可選擇輸出格式：草稿（含 next_hook 標記）或乾淨稿

### 5-4 多文件支援

目前系統是單一 `state.json`。
新增 `document_id` 層級，讓同一個 Lore Bible 可以被多份文件共用（對「神人戰記」多卷結構有用）。

---

## 優先序建議

```
Phase 1（本次）→ Phase 2 → Phase 3 → Phase 4-1+4-2 → Phase 4-3+4-4 → Phase 5
```

Phase 3 的 ADHD UX 功能比 Web UI 更重要，因為它直接影響日常使用體驗。
建議在做 Web UI 之前先在 CLI 層驗證 UX 邏輯是否有效。
