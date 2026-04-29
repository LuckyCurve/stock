"""交互式抓取 roic.ai 财报数据到 roic_cache/ 目录。

用法:
    python src/fetch.py

输入 ticker（空格或逗号分隔），脚本会逐个抓取，已缓存的自动跳过。
"""

import os
import sys
import subprocess


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(SCRIPT_DIR, "roic_cache")


def fetch_ticker(ticker):
    ticker = ticker.strip().upper()
    if not ticker:
        return

    # 文件名：BRK.B → BRK_B.yaml
    filename = ticker.replace(".", "_") + ".yaml"
    filepath = os.path.join(CACHE_DIR, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        print(f"  [CACHE] {ticker} 已缓存 → {filename}")
        return

    print(f"  [FETCH] {ticker} ...", end=" ", flush=True)
    try:
        result = subprocess.run(
            f'opencli roic financials {ticker}',
            capture_output=True,
            text=True,
            timeout=60,
            shell=True,
        )
        output = result.stdout.strip()
        if not output:
            print("失败（无输出）")
            return

        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(output)

        if os.path.getsize(filepath) > 0:
            lines = output.count("\n") + 1
            print(f"完成（{lines} 行）")
        else:
            os.remove(filepath)
            print("失败（空文件）")

    except FileNotFoundError:
        print("失败（opencli 未安装或不在 PATH 中）")
    except subprocess.TimeoutExpired:
        print("失败（超时 60s）")
    except Exception as e:
        print(f"失败（{e}）")
        if os.path.exists(filepath) and os.path.getsize(filepath) == 0:
            os.remove(filepath)


def main():
    print("=" * 50)
    print("  财报数据抓取工具")
    print(f"  缓存目录: {CACHE_DIR}")
    print("=" * 50)

    # 列出已有缓存
    if os.path.exists(CACHE_DIR):
        existing = [f for f in os.listdir(CACHE_DIR) if f.endswith(".yaml")]
        if existing:
            tickers = [f.replace(".yaml", "") for f in sorted(existing)]
            print(f"\n  已缓存 {len(existing)} 个: {', '.join(tickers)}")

    print()
    print("  输入 ticker（空格或逗号分隔），回车执行，空行退出")
    print("  示例: AAPL MSFT GOOGL")
    print("  示例: BRK.B, JPM, V")
    print()

    while True:
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  退出")
            break

        if not raw:
            print("  退出")
            break

        # 支持空格和逗号分隔
        tickers = [t.strip() for t in raw.replace(",", " ").split() if t.strip()]
        if not tickers:
            continue

        print()
        for ticker in tickers:
            fetch_ticker(ticker)
        print()


if __name__ == "__main__":
    main()
