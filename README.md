# claude-code-cli-lab

以 Python 自動化驅動 Claude Code CLI 非互動模式的實驗專案，用於 CCFA 考試準備。

## 專案目標

示範如何在 Python 腳本中呼叫 Claude Code CLI，並解析結構化輸出，涵蓋三個核心 CLI 參數的實際應用：

| 參數 | 說明 |
|---|---|
| `-p` / `--print` | 非互動模式，執行一次後退出 |
| `--output-format json` | 將 CLI 回應包裝成 JSON envelope 輸出 |
| `--json-schema` | 強制輸出符合指定 JSON Schema 的結構（目前版本有 hang 問題，以 prompt 指令替代） |

## 檔案結構

```
claude-code-cli-lab/
├── code_review.py       # 主程式：呼叫 Claude CLI 做程式碼審查
├── demo_api.py          # 受測目標：多 provider LLM API 示範腳本
├── review_schema.json   # 期望的 JSON Schema（供參考，未啟用）
└── review_output.json   # 審查結果輸出（執行後產生）
```

## 快速開始

```bash
python code_review.py .\demo_api.py
```

輸出範例：

```
=== 審查報告：.\demo_api.py ===
評分：58/100
摘要：結構清晰，適合教學用途，但有大量重複程式碼...

[HIGH] 第 18 行 GOOGLE_MODEL 預設值是錯誤的模型名稱，會導致執行時 API 錯誤。
[HIGH] 缺少 if __name__ == "__main__": 保護...
[MEDIUM] 三個分支程式碼幾乎完全相同，應抽取為共用函式...
```

完整結構化結果同步寫入 `review_output.json`。

## CLI 輸出結構

`--output-format json` 回傳的 JSON envelope 格式：

```json
{
  "type": "result",
  "subtype": "success",
  "result": "<Claude 的純文字或 JSON 回應>",
  "duration_ms": 4637,
  "total_cost_usd": 0.0012,
  "session_id": "...",
  "usage": { "input_tokens": 120, "output_tokens": 85 }
}
```

`result` 欄位是 Claude 的原始回應字串。若 prompt 要求 JSON 格式，需對 `result` 再做一次 `json.loads()`。

## Windows 環境注意事項

在 Windows 上用 Python subprocess 呼叫 Claude Code CLI 有三個已知問題：

### 1. `text=True` 導致 stdout 靜默消失

`subprocess.run(..., capture_output=True, text=True)` 在中文 Windows 系統使用 cp950 解碼，Claude 輸出的 UTF-8 bytes 會被靜默丟棄。

```python
# 錯誤做法
result = subprocess.run([...], capture_output=True, text=True)

# 正確做法
result = subprocess.run([...], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
text = result.stdout.decode("utf-8")
```

### 2. `claude.cmd` 的管道符號問題

npm 安裝的 `claude.cmd` 透過 `%*` 展開所有參數。若 prompt 含有 `|` 字符，cmd.exe 會將其解讀為 pipe 運算子，導致 `--output-format json` 等後續參數被截斷。

```python
# 繞過方式：直接呼叫 .exe，不經 .cmd 包裝
CLAUDE_EXE = r"C:\Users\<user>\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"
```

### 3. Python console 中文輸出編碼

Windows PowerShell 預設 cp1252，`print()` 中文字串會拋出 `UnicodeEncodeError`。

```python
import sys
sys.stdout.reconfigure(encoding="utf-8")
```

## 需求

- Python 3.10+
- Claude Code CLI（`npm install -g @anthropic-ai/claude-code`）
- 已登入 Claude Code（`claude` 可正常執行）

## FAQ：認證模式與計費

### Claude Pro 登入 vs API Key 登入

`code_review.py` 透過 `subprocess` 呼叫 `claude.exe`，**完全沒有 API Key**，這是因為 Claude Code CLI 是一個「已登入的客戶端應用程式」，認證在登入時（`claude login`）就完成並儲存在本機，每次執行自動讀取既有憑證。

| 模式 | 認證方式 | 計費 |
|---|---|---|
| API 直連（`demo_api.py`） | 程式內傳入 `ANTHROPIC_API_KEY` | 依 token 用量計費 |
| Claude Code CLI（`code_review.py`） | CLI 登入時的本機憑證 | 取決於登入帳號類型 |

執行 `claude /status` 可確認目前登入方式。本專案測試環境為 **Claude Pro account** 登入，因此 `-p` 模式跑批次審查**不會產生額外 API 帳單**，用量計入 Claude Pro 的訂閱使用額度（usage limit），與互動式 Claude Code、claude.ai 網頁共用同一額度池。

### `-p` 模式 ≠ 不計費，而是「計費方式不同」

常聽到「`-p` 模式不用 API 用量」這句話，準確說法是：

- **`-p` / `--print`** 本身只是控制執行方式（非互動、跑一次後退出），跟計費邏輯無關
- 是否算「API 用量」取決於 **CLI 登入的帳號類型**：
  - Claude Pro / Max 訂閱登入 → 算入訂閱額度，不額外計費，但仍有 rate limit 上限
  - API Key 登入 → 一樣按 token 計費，只是由 CLI 代為呼叫

### API 直連 vs CLI 模式的速度差異

兩者模型推論本身速度相同，差異主要來自 **CLI 啟動開銷**（載入設定、檢查憑證、初始化 session 等）：

- 單次任務：差異通常可忽略
- 批次/高頻任務（如逐檔案跑 `code_review.py`）：CLI 模式累積的啟動成本較明顯，API 直連通常較快

`review_output.json` 中的 `duration_ms` 為純模型處理時間，不含 CLI 啟動開銷，可作為對照基準。

### `-p` 模式的設計理念

`-p` / `--print`（headless mode）的核心設計目標是讓 Claude Code **像一般 Unix 命令列工具一樣可組合（composable）**：

- 取代舊版 `--headless` flag，讓 CLI 可在無人值守情況下運行（git push、PR 留言、cron job、CI 階段觸發）
- 輸出機器可讀的結果（搭配 `--output-format json`），可串接其他工具：例如 Claude 分析程式碼輸出 JSON → Python 腳本讀取並發送 Slack → 另一次 Claude 呼叫根據回應更新文件，每一步都是獨立 process
- 與一般固定腳本不同，模型針對當前上下文進行推理並決定該做什麼，而非執行死板的步驟

簡言之：將「互動式 AI 編程助手」封裝成符合 Unix 哲學（stdin/stdout、exit code、可 pipe、可組合）的命令列工具，使其能無縫嵌入既有自動化生態系，這正是本專案 `code_review.py` 的設計動機——把 AI 推理包裝成可被傳統程式呼叫、解析、串接的「函式」。

### 何時該升級到 API Key 模式

- 個人或小規模自動化（單一 CI 流程、git hook、少量批次審查）：Pro/Max 訂閱下的 `-p` 模式已足夠，且更划算
- 大規模/高頻自動化（並行多 agent、整夜批次、CI/CD 大量觸發）：建議改用 API Key，因為 Pro/Max 的 rate limit 是共享額度，容易在大量平行呼叫時觸頂。`code_review.py` 程式碼無需修改，只需更換登入憑證即可
