import subprocess
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")


CLAUDE_EXE = r"C:\Users\X570\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"


def review_file(filepath: str) -> dict:
    prompt = (
        f"審查這個檔案的程式碼品質：{filepath}，指出潛在問題並給出評分。\n\n"
        "只輸出以下 JSON 格式，不要包含任何其他文字或 markdown：\n"
        '{"summary": "整體評估字串", '
        '"issues": [{"severity": "high 或 medium 或 low", "line": 行號整數或null, "message": "問題描述"}], '
        '"score": 0到100的整數}'
    )

    result = subprocess.run(
        [CLAUDE_EXE, "--print", prompt, "--output-format", "json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI 錯誤: {result.stderr.decode('utf-8', errors='replace')}")

    envelope = json.loads(result.stdout.decode("utf-8"))
    review_data = json.loads(envelope["result"])
    return review_data


def print_report(filepath: str, review: dict) -> None:
    print(f"\n=== 審查報告：{filepath} ===")
    print(f"評分：{review['score']}/100")
    print(f"摘要：{review['summary']}\n")

    if not review["issues"]:
        print("未發現問題。")
        return

    for issue in sorted(review["issues"], key=lambda x: x["severity"]):
        line_info = f"第 {issue['line']} 行 " if issue.get("line") else ""
        print(f"[{issue['severity'].upper()}] {line_info}{issue['message']}")


def main():
    if len(sys.argv) < 2:
        print("用法: python code_review.py <檔案路徑>")
        sys.exit(1)

    filepath = sys.argv[1]
    review = review_file(filepath)
    print_report(filepath, review)

    with open("review_output.json", "w", encoding="utf-8") as f:
        json.dump(review, f, ensure_ascii=False, indent=2)
    print("\n完整報告已寫入 review_output.json")


if __name__ == "__main__":
    main()
