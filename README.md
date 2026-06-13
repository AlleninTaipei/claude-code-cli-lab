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
