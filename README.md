# Divergent Writing Engine (Prototype)

這個專案把你提出的 ADHD 寫作環境概念，落地為「可執行的多代理系統骨架」。

## 目標
- 10x10 全局熱力圖（藍圖區）
- 原子片段生命週期與返回鉤子
- 四大窄模式作業區（Catcher / Expander / Blueprint / Lore Bible）
- 嚴格防腦補邊界（Lore 與擴寫流程隔離）
- OpenRouter + Multi-Agent + Tool Call

## 快速開始
```bash
export OPENROUTER_API_KEY="<your-key>"
python app/main.py init
python app/main.py capture --text "雨夜，主角忘了密碼"
python app/main.py expand --fragment-id <id>
python app/main.py board
```

## 系統分層
1. `app/orchestrator.py`: 多代理編排器（可為不同代理指定不同模型）。
2. `app/openrouter_client.py`: OpenRouter OpenAI-compatible chat + tool calls。
3. `app/tools.py`: 唯一可執行動作集合（寫作環境的行為邊界）。
4. `app/store.py`: 本地 JSON 狀態儲存（片段、熱力圖、Lore）。
5. `config/agents.json`: 每個 agent 的模型、system prompt、工具權限。

詳細設計請看 `docs/architecture.md`。
