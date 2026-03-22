import yfinance as yf

# ═══════════════════════════════════════════
# 📐 函式定義
# ═══════════════════════════════════════════

def get_pcr(symbol: str):
    """
    計算個股的 Put-Call Ratio（PCR）
    抓取最近 3 個到期日的選擇權資料加總計算
    """
    tk = yf.Ticker(symbol)

    # 取得所有到期日
    expirations = tk.options
    if not expirations:
        print(f"❌ 找不到 {symbol} 的選擇權資料，請確認代碼是否正確。")
        return None

    total_put  = 0
    total_call = 0

    # 只取最近 3 個到期日（資料最充足）
    for date in expirations[:3]:
        chain = tk.option_chain(date)
        total_put  += chain.puts['volume'].fillna(0).sum()
        total_call += chain.calls['volume'].fillna(0).sum()

    if total_call == 0:
        print(f"⚠️  {symbol} 的 Call 成交量為 0，無法計算 PCR。")
        return None

    pcr = total_put / total_call
    return pcr


def score_pcr(pcr: float) -> dict:
    """
    根據 PCR 數值給出情緒評分與說明
    """
    if 0.7 <= pcr <= 1.0:
        sentiment  = "中立 😐"
        desc       = "市場情緒中立，不確定因素性高"
        suggestion = "觀望為主，等待方向確認後再行動"
    elif pcr < 0.7:
        sentiment  = "樂觀 🟢"
        desc       = "市場情緒較樂觀，Call 買盤強勁"
        suggestion = "市場偏多，但需留意過度樂觀帶來的回落風險"
    else:  # pcr > 1.0
        sentiment  = "悲觀 🔴"
        desc       = "市場情緒較悲觀，Put 買盤強勁"
        suggestion = "市場偏空，但逆向思考：極度悲觀時往往是潛在買點"

    return {
        "sentiment":  sentiment,
        "desc":       desc,
        "suggestion": suggestion,
    }


def analyze(symbol: str):
    """
    主分析函式：抓取 PCR 並輸出完整報告
    """
    symbol = symbol.upper().strip()
    print(f"\n{'=' * 45}")
    print(f"  {symbol} - Put-Call Ratio 情緒分析")
    print(f"{'=' * 45}")

    pcr = get_pcr(symbol)
    if pcr is None:
        return

    result = score_pcr(pcr)

    print(f"  PCR 數值    : {pcr:.4f}")
    print(f"  市場情緒    : {result['sentiment']}")
    print(f"  情緒說明    : {result['desc']}")
    print(f"  參考建議    : {result['suggestion']}")
    print(f"{'-' * 45}")
    print(f"  評分依據：")
    print(f"    PCR 0.7 ~ 1.0  ->  中立（不確定因素高）")
    print(f"    PCR < 0.7      ->  樂觀（Call 主導）")
    print(f"    PCR > 1.0      ->  悲觀（Put 主導）")
    print(f"{'=' * 45}\n")


# ═══════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 44)
    print("   PCR 市場情緒分析工具  v1.0")
    print("   資料來源：Yahoo Finance (yfinance)")
    print("=" * 44)
    print("  輸入 q 離開程式\n")

    while True:
        symbol = input("  請輸入股票代碼（例如 AAPL、TSLA、SPY）：").strip()

        if symbol.lower() in ('q', 'quit', 'exit'):
            print("\n  已離開程式，再見！\n")
            break

        if not symbol:
            print("  請輸入股票代碼\n")
            continue

        analyze(symbol)
