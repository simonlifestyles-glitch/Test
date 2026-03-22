import pandas as pd
import matplotlib.pyplot as plt
import math
import yfinance as yf

# ═══════════════════════════════════════════
# 📐 函式定義
# ═══════════════════════════════════════════

def variance_calculator(series, series_average, win_len):
    sma = win_len
    temp  = series.subtract(series_average)
    temp2 = temp.apply(lambda x: x**2)
    temp3 = temp2.rolling(sma - 1).mean()
    sigma = temp3.apply(lambda x: math.sqrt(x))
    return sigma


# ═══════════════════════════════════════════
# 📥 資料載入
# ═══════════════════════════════════════════

print("正在下載 S&P 500 期貨資料...")
futures = yf.download('ES=F', start="2017-07-31", auto_adjust=True)
futures.index = pd.to_datetime(futures.index).normalize()
if futures.index.tz is not None:
    futures.index = futures.index.tz_localize(None)

def load_cboe_pcr(url):
    """讀取 CBOE PCR CSV，自動處理欄位與格式"""
    df = pd.read_csv(url, skiprows=1, header=None, encoding='latin-1')
    df = df.iloc[:, [0, -1]].copy()
    df.columns = ['Date', 'PCR']
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df['PCR'] = pd.to_numeric(df['PCR'], errors='coerce')
    df = df.dropna(subset=['PCR'])
    df = df.set_index('Date')
    df.index = df.index.normalize()
    return df

print("正在下載 CBOE Put-Call Ratio 資料（舊檔 2003~2012）...")
pcr_old = load_cboe_pcr(
    "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/indexpcarchive.csv"
)
print(f"舊檔範圍：{pcr_old.index.min().date()} ~ {pcr_old.index.max().date()}，共 {len(pcr_old)} 筆")

print("正在下載 CBOE Put-Call Ratio 資料（新檔 2012~今）...")
pcr_new = load_cboe_pcr(
    "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/indexpc.csv"
)
print(f"新檔範圍：{pcr_new.index.min().date()} ~ {pcr_new.index.max().date()}，共 {len(pcr_new)} 筆")

# 合併新舊資料並去重
pcr_raw = pd.concat([pcr_old, pcr_new])
pcr_raw = pcr_raw[~pcr_raw.index.duplicated(keep='last')]
pcr_raw = pcr_raw.sort_index()

print(f"\nPCR 資料範圍：{pcr_raw.index.min().date()} ~ {pcr_raw.index.max().date()}，共 {len(pcr_raw)} 筆")
print(f"期貨資料範圍：{futures.index.min().date()} ~ {futures.index.max().date()}，共 {len(futures)} 筆")

# 合併兩份資料
Data = futures[['Close']].copy()
Data.columns = ['future']
Data['PCR'] = pcr_raw['PCR']
Data = Data.dropna()
Data = Data[Data.index >= '2017-07-31']
Data = Data.reset_index()
Data.columns.values[0] = 'Date'

print(f"\n資料載入完成，共 {len(Data)} 筆，時間範圍：{Data['Date'].iloc[0].date()} ~ {Data['Date'].iloc[-1].date()}")
print(Data.head())


# ═══════════════════════════════════════════
# ⚙️ 參數設定
# ═══════════════════════════════════════════

sma    = 20
k      = 1.5
l      = 2
abs_SL = 25

pro        = 0
flag       = 1
buy_flag   = False
sell_flag  = False
transaction_start_price = 0

mtm         = []
order       = []
profit      = []
buy_sell    = []
stoploss    = []
trade_cause = []


# ═══════════════════════════════════════════
# 📊 計算技術指標
# ═══════════════════════════════════════════

Data['mAvg']     = Data['PCR'].rolling(sma).mean()
Data['PCR_prev'] = Data['PCR'].shift(1)

sigma   = variance_calculator(Data['PCR'], Data['mAvg'], sma)
k_sigma = k * sigma
l_sigma = l * sigma

Data['UBB'] = Data['mAvg'].add(k_sigma)
Data['LBB'] = Data['mAvg'].subtract(k_sigma)
Data['USL'] = Data['UBB'].add(l_sigma)
Data['LSL'] = Data['LBB'].subtract(l_sigma)


# ═══════════════════════════════════════════
# 🔁 策略主迴圈
# ═══════════════════════════════════════════

s = len(Data)

for i in range(s):

    pro         = 0
    future_cost = Data['future'].iloc[i]
    PCR         = Data['PCR'].iloc[i]
    PCR_prev    = Data['PCR_prev'].iloc[i]
    LBB         = Data['LBB'].iloc[i]
    UBB         = Data['UBB'].iloc[i]
    mAvg        = Data['mAvg'].iloc[i]
    USL         = Data['USL'].iloc[i]
    LSL         = Data['LSL'].iloc[i]

    UBB_cross       = (PCR > UBB)  and (PCR_prev < UBB)
    LBB_cross       = (PCR < LBB)  and (PCR_prev > LBB)
    mAvg_cross_up   = (PCR > mAvg) and (PCR_prev < mAvg)
    mAvg_cross_down = (PCR < mAvg) and (PCR_prev > mAvg)
    USL_cross       = (PCR > USL)  and (PCR_prev < USL)
    LSL_cross       = (PCR < LSL)  and (PCR_prev > LSL)

    if UBB_cross and (not buy_flag) and flag == 1:
        flag = 0; buy_flag = True; sell_flag = False
        transaction_start_price = future_cost
        order_details = [1, "Buy", "UBB Crossed", "0", "Position taken"]

    elif LBB_cross and (not sell_flag) and flag == 1:
        flag = 0; sell_flag = True; buy_flag = False
        transaction_start_price = future_cost
        order_details = [-1, "Sell", "LBB Crossed", "0", "Position taken"]

    elif mAvg_cross_up and (not buy_flag) and flag == 0:
        flag = 1; buy_flag = False; sell_flag = False
        pro = future_cost - transaction_start_price
        order_details = [1, "Buy", "mAvg Crossed", "0", "Position Closed"]

    elif LSL_cross and (not buy_flag) and flag == 0:
        flag = 1; buy_flag = False; sell_flag = False
        pro = future_cost - transaction_start_price
        order_details = [1, "Buy", "LSL Crossed", "Stoploss Executed", "Position Closed"]

    elif (future_cost - transaction_start_price) > abs_SL and (not buy_flag) and flag == 0:
        flag = 0; buy_flag = False; sell_flag = False
        pro = future_cost - transaction_start_price
        order_details = [1, "Buy", "Abs SL", "Stoploss Executed", "Position Closed"]

    elif mAvg_cross_down and (not sell_flag) and flag == 0:
        flag = 1; buy_flag = False; sell_flag = False
        pro = -(future_cost - transaction_start_price)
        order_details = [-1, "Sell", "mAvg Crossed (H to L)", "0", "Position Closed"]

    elif USL_cross and (not sell_flag) and flag == 0:
        flag = 1; buy_flag = False; sell_flag = False
        pro = -(future_cost - transaction_start_price)
        order_details = [-1, "Sell", "USL Crossed", "Stoploss Executed", "Position Closed"]

    elif (-future_cost + transaction_start_price) > abs_SL and (not sell_flag) and flag == 0:
        flag = 1; buy_flag = False; sell_flag = False
        pro = -(future_cost - transaction_start_price)
        order_details = [-1, "Sell", "Abs SL", "Abs Stoploss Executed", "Position Closed"]

    else:
        if not buy_flag and not sell_flag:
            tempo = 0
        elif buy_flag:
            tempo = (Data['future'].iloc[i] - transaction_start_price) * 500
        else:
            tempo = (-Data['future'].iloc[i] + transaction_start_price) * 500
        order_details = [0, "No Trade", "No Trade", "0", tempo]

    profit.append(pro)
    order.append(order_details[0])
    buy_sell.append(order_details[1])
    trade_cause.append(order_details[2])
    stoploss.append(order_details[3])
    mtm.append(order_details[4])


# ═══════════════════════════════════════════
# 💰 資金計算
# ═══════════════════════════════════════════

Data['placed_order'] = pd.Series(order)
Data['cost']         = -(Data['placed_order'].multiply(Data['future'])) * 500
Data['out']          = Data['cost'].cumsum()
Data['buy_sell']     = pd.Series(buy_sell)
Data['profit']       = -pd.Series(profit) * 500
Data['stoploss']     = pd.Series(stoploss)
Data['trade_cause']  = pd.Series(trade_cause)
Data['mtm']          = pd.Series(mtm)

print("\n累計損益（最後10筆）：")
print(Data['out'].tail(10))


# ═══════════════════════════════════════════
# 📤 輸出 Excel
# ═══════════════════════════════════════════

output = pd.DataFrame()
output['Date']         = Data['Date']
output['Close']        = Data['future']
output['PCR']          = Data['PCR']
output['placed_order'] = Data['placed_order']
output['buy_sell']     = Data['buy_sell']
output['trade_cause']  = Data['trade_cause']
output['PnL']          = Data['profit']
output['mtm']          = Data['mtm']
output['stoploss']     = Data['stoploss']
output['Cash Account'] = Data['out']

output.to_excel('PCR_SL_output.xlsx', sheet_name='Sheet1', index=False)
print("\n結果已儲存至 PCR_SL_output.xlsx")


# ═══════════════════════════════════════════
# 📈 繪圖
# ═══════════════════════════════════════════

fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

axes[0].plot(Data['Date'], Data['PCR'],  label='PCR',  color='blue',      lw=1.5)
axes[0].plot(Data['Date'], Data['mAvg'], label='mAvg', color='orange',    lw=1.5)
axes[0].plot(Data['Date'], Data['UBB'],  label='UBB',  color='green',     lw=1, linestyle='--')
axes[0].plot(Data['Date'], Data['LBB'],  label='LBB',  color='red',       lw=1, linestyle='--')
axes[0].plot(Data['Date'], Data['USL'],  label='USL',  color='darkgreen', lw=1, linestyle=':')
axes[0].plot(Data['Date'], Data['LSL'],  label='LSL',  color='darkred',   lw=1, linestyle=':')
axes[0].set_title('SPX Put-Call Ratio + Bollinger Bands')
axes[0].set_ylabel('PCR')
axes[0].legend(loc='upper right')
axes[0].grid(True, alpha=0.3)

axes[1].plot(Data['Date'], Data['out'], label='Cumulative P&L', color='purple', lw=1.5)
axes[1].axhline(0, color='gray', linestyle='--', lw=1)
axes[1].set_title('Cumulative P&L (USD)')
axes[1].set_ylabel('P&L ($)')
axes[1].set_xlabel('Date')
axes[1].legend(loc='upper left')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('PCR_strategy_chart.png', dpi=150)
plt.show()
print("圖表已儲存至 PCR_strategy_chart.png")
