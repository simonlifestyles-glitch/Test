# PCR 市場情緒分析工具

> 輸入股票代碼，即時計算 **Put-Call Ratio（PCR）** 並解讀市場情緒

---

## 一、什麼是 Put/Call Ratio（PCR）？

Put-Call Ratio 是選擇權市場中最常用的**市場情緒指標**之一。

### 計算公式

```
PCR = Put 成交量（或未平倉量）/ Call 成交量（或未平倉量）
```

### 意義

選擇權分為兩種：
- **Call（買權）**：買入的人預期價格**上漲**
- **Put（賣權）**：買入的人預期價格**下跌**

當市場上買 Put 的人越多，PCR 就越高，代表市場情緒越悲觀；反之，買 Call 的人越多，PCR 越低，代表市場情緒越樂觀。

### 評分標準

| PCR 數值 | 市場情緒 | 說明 |
|---|---|---|
| PCR < 0.7 | 樂觀 | Call 主導，市場偏多，需留意過度樂觀的回落風險 |
| PCR 0.7 ~ 1.0 | 中立 | 買賣力道接近，市場不確定性高，方向不明 |
| PCR > 1.0 | 悲觀 | Put 主導，市場偏空，但逆向思考也可能是潛在買點 |

### PCR 作為逆向指標

PCR 常被當作**逆向指標（Contrarian Indicator）**使用：

> 當所有人都在恐慌買 Put，市場往往已接近底部；
> 當所有人都過度樂觀買 Call，市場往往已接近頂部。

這也是為什麼 PCR 在量化交易中常被搭配布林通道使用——突破極端值時，反向操作。

---

## 二、Volume vs Open Interest 的差異

本工具提供兩個版本，分別使用不同的計算基準：

### Volume（成交量）

- **定義**：當天已成交的選擇權合約口數
- **更新頻率**：盤中**即時**更新
- **反映的資訊**：今日市場的**即時情緒與交易活躍度**
- **適合用途**：當日盤中整體情緒判斷
- **注意事項**：開盤初期成交量少，PCR 數字可能偏差較大，建議在盤中後段查詢

### Open Interest（未平倉量）

- **定義**：目前市場上**尚未平倉**的選擇權合約總口數
- **更新頻率**：**每日收盤後**更新，隔日才反映
- **反映的資訊**：市場參與者的**累積整體部位**與支撐壓力結構
- **適合用途**：中長線、找出市場關鍵支撐位與壓力位
- **注意事項**：資料有一天延遲，盤中數字不會即時變動

### 一句話比較

```
Volume  = 今天大家買賣了多少  →  反應快，反映即時情緒
OI      = 大家目前累積押了多少 →  反應慢，反映市場結構
```

### 對照表

| 項目 | Volume（成交量） | Open Interest（未平倉量） |
|---|---|---|
| 更新頻率 | 即時 | 每日收盤後 |
| 反映時間軸 | 當日短線 | 中長線累積 |
| 涵蓋範圍 | 全部到期日加總 | 全部到期日 × 全部履約價 |
| 輸出結果 | PCR 數值 + 情緒判斷 | OI 分布圖 + 支撐壓力位 |
| 適合用途 | 盤中快速情緒判斷 | 找關鍵支撐 / 壓力位 |

---

## 三、程式抓取邏輯

### 資料來源

- **套件**：`yfinance`（Yahoo Finance 免費公開資料）
- **無需 API Key**，無需帳號

---

### Volume 版（`pcr_volume.py`）

**核心概念：**
涵蓋所有到期日（短中長期）的當日成交量，反映投資者今日整體的看漲 / 看跌傾向。

**抓取步驟：**

```
輸入股票代碼（例如 AAPL）
        ↓
用 yfinance 取得該股所有選擇權到期日列表
        ↓
遍歷「全部到期日」（短中長期都包含）
        ↓
每個到期日抓取當日 Put / Call 的成交量（volume）
        ↓
加總全部到期日的 Put 成交量 / Call 成交量
        ↓
計算 PCR = 總 Put 成交量 / 總 Call 成交量
        ↓
對照評分標準，輸出情緒判斷與建議
```

**為什麼取全部到期日？**

投資者買選擇權的目的不同：
- 短線投機者 → 買近月合約
- 避險投資者 → 買遠月合約
- 法人機構 → 布局多個到期日

只取近月會遺漏中長期部位的情緒，全部加總才能反映完整的市場看法。

**程式碼核心：**

```python
for date in expirations:       # 全部到期日，不設上限
    chain = tk.option_chain(date)
    total_put  += chain.puts['volume'].fillna(0).sum()
    total_call += chain.calls['volume'].fillna(0).sum()

pcr = total_put / total_call
```

**輸出範例：**

```
==================================================
  AAPL - PCR 情緒分析 ( 成交量版 )
==================================================
  計算方式    : 當日成交量 (Volume)，全部到期日
  適合用途    : 反映投資者今日短中長期整體看法
  Put 成交量  : 128,450
  Call 成交量 : 185,320
  PCR 數值    : 0.6932
  市場情緒    : 樂觀
  情緒說明    : 市場情緒較樂觀，Call 買盤強勁
  參考建議    : 市場偏多，但需留意過度樂觀帶來的回落風險
```

---

### OI 版（`pcr_open_interest.py`）

**核心概念：**
以「全部到期日 × 全部履約價」的 OI 分布，找出市場的關鍵支撐位（Put Wall）和壓力位（Call Wall）。

**抓取步驟：**

```
輸入股票代碼（例如 AAPL）
        ↓
用 yfinance 取得該股所有選擇權到期日列表
        ↓
遍歷「全部到期日」
        ↓
每個到期日抓取所有履約價的 Put / Call 未平倉量（openInterest）
        ↓
依照「履約價」為軸，跨到期日加總 OI
（每個履約價的 Put OI = 所有到期日在此履約價的 OI 加總）
        ↓
找出 Call OI 最大的履約價 → Call Wall（壓力位）
找出 Put OI 最大的履約價  → Put Wall（支撐位）
        ↓
畫出分布圖，標示現價 / Call Wall / Put Wall
同時計算整體 PCR 輸出情緒判斷
```

**Call Wall / Put Wall 是什麼？**

| 名稱 | 定義 | 市場意義 |
|---|---|---|
| **Call Wall** | Call OI 最大的履約價 | 賣 Call 的莊家會在此履約價附近壓制股價，形成**短期壓力** |
| **Put Wall** | Put OI 最大的履約價 | 賣 Put 的莊家會在此履約價附近護盤，形成**短期支撐** |

**為什麼要跨到期日加總？**

同一個履約價（例如 AAPL $200）可能存在於多個到期日：
- 3月到期的 $200 Call：OI 5,000
- 6月到期的 $200 Call：OI 8,000
- 9月到期的 $200 Call：OI 3,000

加總後這個履約價的 Call OI = 16,000，才能完整反映市場在此價位堆積的部位量。

**程式碼核心：**

```python
# 遍歷全部到期日，收集所有履約價的 OI
for date in expirations:
    chain = tk.option_chain(date)
    all_calls.append(chain.calls[['strike', 'openInterest']])
    all_puts.append(chain.puts[['strike', 'openInterest']])

# 依履約價加總（跨所有到期日）
df_calls = pd.concat(all_calls).groupby('strike')['openInterest'].sum()
df_puts  = pd.concat(all_puts).groupby('strike')['openInterest'].sum()

# 找出 Wall
call_wall = df_calls.idxmax()   # Call OI 最大的履約價
put_wall  = df_puts.idxmax()    # Put OI 最大的履約價
```

**輸出範例：**

```
==================================================
  AAPL - OI Distribution Report
==================================================
  Current Price : 213.49
  Call Wall     : Strike 220.0  (OI: 98,432)  <- Resistance
  Put Wall      : Strike 200.0  (OI: 76,210)  <- Support
  Overall PCR   : 0.8834  ->  中立 (Put/Call 接近)
```

---

## 四、兩版本比較總結

| | Volume 版 | OI 版 |
|---|---|---|
| **檔案** | `pcr_volume.py` | `pcr_open_interest.py` |
| **計算欄位** | `volume` | `openInterest` |
| **涵蓋範圍** | 全部到期日 | 全部到期日 × 全部履約價 |
| **輸出** | PCR 數值 + 情緒文字 | OI 分布圖 + 支撐壓力位 |
| **資料即時性** | 盤中即時 | 前一日收盤後更新 |
| **適合用途** | 快速判斷今日情緒 | 找關鍵支撐 / 壓力位 |

---

## 五、安裝與執行

### 安裝套件

```bash
pip install yfinance pandas matplotlib
```

### 執行

```bash
# 即時情緒版（Volume）
python pcr_volume.py

# OI 分布圖版（Open Interest）
python pcr_open_interest.py
```

---

## 六、免責聲明

本工具僅供**學術研究與學習用途**，不構成任何投資建議。
選擇權市場具有高度風險，請自行評估後謹慎操作。
