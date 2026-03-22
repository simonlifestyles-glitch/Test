import yfinance as yf

# ═══════════════════════════════════════════
# 📐 函式定義
# ═══════════════════════════════════════════

def get_pcr_volume(symbol: str):
    """
    計算個股的 Put-Call Ratio（PCR）
    使用當日成交量（Volume）計算
    反映：今日即時市場情緒
    """
    tk = yf.Ticker(symbol)

    expirations = tk.options
    if not expirations:
        print(f"找不到 {symbol} 的選擇權資料，請確認代碼是否正確。")
        return None

    total_put  = 0
    total_call = 0

    for date in expirations[:3]:  # 最近 3 個到期日
        chain = tk.option_chain(date)
        total_put  += chain.puts['volume'].fillna(0).sum()
        total_call += chain.calls['volume'].fillna(0).sum()

    if total_call == 0:
        print(f"  {symbol} 的 Call 成交量為 0，無法計算 PCR。")
        return None

    return total_put / total_call


def score_pcr(pcr: float) -> dict:
    if 0.7 <= pcr <= 1.0:
        return {
            "sentiment":  "中立",
            "desc":       "市場情緒中立，不確定因素性高",
            "suggestion": "觀望為主，等待方向確認後再行動",
        }
    elif pcr < 0.7:
        return {
            "sentiment":  "樂觀",
            "desc":       "市場情緒較樂觀，Call 買盤強勁",
            "suggestion": "市場偏多，但需留意過度樂觀帶來的回落風險",
        }
    else:
        return {
            "sentiment":  "悲觀",
            "desc":       "市場情緒較悲觀，Put 買盤強勁",
            "suggestion": "市場偏空，但逆向思考：極度悲觀時往往是潛在買點",
        }


def analyze(symbol: str):
    symbol = symbol.upper().strip()
    print(f"\n{'=' * 47}")
    print(f"  {symbol} - PCR 情緒分析 ( 成交量版 )")
    print(f"{'=' * 47}")

    pcr = get_pcr_volume(symbol)
    if pcr is None:
        return

    result = score_pcr(pcr)

    print(f"  計算方式    : 當日成交量 (Volume)")
    print(f"  適合用途    : 盤中即時情緒判斷")
    print(f"  PCR 數值    : {pcr:.4f}")
    print(f"  市場情緒    : {result['sentiment']}")
    print(f"  情緒說明    : {result['desc']}")
    print(f"  參考建議    : {result['suggestion']}")
    print(f"{'-' * 47}")
    print(f"  評分依據：")
    print(f"    PCR 0.7 ~ 1.0  ->  中立 (不確定因素高)")
    print(f"    PCR < 0.7      ->  樂觀 (Call 主導)")
    print(f"    PCR > 1.0      ->  悲觀 (Put 主導)")
    print(f"{'=' * 47}\n")


# ═══════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 47)
    print("   PCR 市場情緒分析 - 成交量版  v1.0")
    print("   資料來源 : Yahoo Finance (yfinance)")
    print("   計算基準 : 當日 Volume，即時反映今日情緒")
    print("=" * 47)
    print("  輸入 q 離開程式\n")

    while True:
        symbol = input("  請輸入股票代碼 (例如 AAPL、TSLA、SPY)：").strip()

        if symbol.lower() in ('q', 'quit', 'exit'):
            print("\n  已離開程式，再見！\n")
            break

        if not symbol:
            print("  請輸入股票代碼\n")
            continue

        analyze(symbol)
