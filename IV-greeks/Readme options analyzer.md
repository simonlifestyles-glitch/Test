# Options Analyzer

> 輸入股票代碼，自動計算並視覺化 **IV、HV、Greeks、Option Price**

---

## 一、這個工具能做什麼？

| 功能 | 說明 |
|---|---|
| **Implied Volatility (IV)** | 從市場報價反推隱含波動率 |
| **Historical Volatility (HV)** | 計算過去 30 日的歷史波動率 |
| **IV vs HV 比較** | 判斷選擇權目前是貴還是便宜 |
| **IV Smile** | 各到期日的 IV 微笑曲線 |
| **IV Term Structure** | ATM IV 隨到期日的期限結構，自動標示異常高 IV |
| **Greeks** | Delta / Gamma / Theta / Vega / Rho |
| **Option Price** | 市場報價 + BSM 理論價格對照 |
| **互動式到期日選擇** | Greeks 圖可自由選擇最多 3 個到期日比較 |
| **CSV 輸出** | 全部合約完整資料匯出 |

---

## 二、核心概念說明

### IV（隱含波動率）vs HV（歷史波動率）

```
HV = 過去 30 天股價的實際波動程度（已發生的事實）
IV = 選擇權市場對未來波動率的預期（市場共識）
```

| IV vs HV | 意義 | 操作參考 |
|---|---|---|
| **IV >> HV** | 選擇權偏貴，市場預期未來波動大 | 賣方策略較有優勢 |
| **IV ≈ HV** | 定價合理 | 中性策略 |
| **IV << HV** | 選擇權偏便宜 | 買方策略較有優勢 |

### IV Smile（微笑曲線）

同一個到期日，不同履約價的 IV 不一樣，畫出來像一個微笑形狀：

```
IV%
 |        *               *
 |     *     *         *     *
 |        *     *   *     *
 |──────────────────────────── Strike
              ATM
```

- **ATM（平價）附近**：IV 通常最低
- **OTM（價外）往兩側**：IV 通常升高（尤其是 Put 側，稱為 Volatility Skew）

### IV Term Structure（期限結構）

ATM 的 IV 隨到期日變化的趨勢：

```
IV%
 |  * 
 |     *
 |        *  *
 |              *  *  *  *
 |────────────────────────── 到期日（近 → 遠）
```

- **正常形狀（近低遠高）**：市場平靜，遠月不確定性較大
- **反轉形狀（近高遠低）**：近月有重大事件（財報 / Fed 會議），短期不確定性高
- **橘色虛線**：HV30 的 1.5 倍門檻，超過此線標示為異常偏高

### Greeks 說明

| Greek | 意義 | 單位 |
|---|---|---|
| **Delta (Δ)** | 股價變動 $1，選擇權價格變動多少 | 0 ~ 1（Call）/ -1 ~ 0（Put） |
| **Gamma (Γ)** | Delta 的變動速率，ATM 時最大 | 每 $1 |
| **Theta (Θ)** | 每天時間流逝，選擇權損失多少價值 | 每天（通常為負） |
| **Vega (V)** | IV 變動 1%，選擇權價格變動多少 | 每 1% IV |
| **Rho (ρ)** | 利率變動 1%，選擇權價格變動多少 | 每 1% 利率 |

---

## 三、程式架構與抓取邏輯

### 資料來源

| 資料 | 來源 | 說明 |
|---|---|---|
| 現價 | yfinance `fast_info` | 即時股價 |
| 選擇權鏈 | yfinance `option_chain()` | 全部到期日的 Call / Put 資料 |
| 歷史股價 | yfinance 過去 90 天 | 用來計算 HV |
| 市場 IV | yfinance `impliedVolatility` 欄位 | Yahoo Finance 提供 |

### 計算模型

| 計算項目 | 優先使用 | Fallback |
|---|---|---|
| IV 反推 | `py_vollib` | 二分法 + `scipy BSM` |
| Greeks | `py_vollib` | `scipy BSM` 解析解 |
| 理論價格 | BSM 公式 | BSM 公式 |

### 完整處理流程

```
輸入股票代碼
        ↓
抓取現價 + 計算 HV（過去 30 日對數報酬標準差 × √252）
        ↓
取得所有到期日列表
        ↓
遍歷每個到期日的選擇權鏈（Call + Put）
        ↓
每筆合約：
  1. 取市場報價 IV（Yahoo Finance 提供）
  2. 若市場 IV 為 0 或異常 → 用 BSM 從市場價格反推 IV
  3. 用 IV + BSM 計算 Delta / Gamma / Theta / Vega / Rho
  4. 用 BSM 計算理論價格
  5. 計算 IV - HV 溢價差
        ↓
輸出文字報告（每個到期日的 ATM 合約）
        ↓
使用者選擇最多 3 個到期日（Greeks 圖用）
        ↓
產生圖表（IV 分析 + Greeks 分析）
        ↓
儲存 CSV（全部合約完整資料）
```

### HV 計算方式

```python
log_returns = ln(Close_t / Close_{t-1})   # 每日對數報酬
HV_30       = std(log_returns, 30天) × √252  # 年化
```

### BSM 公式（Fallback）

```
d1 = [ln(S/K) + (r + σ²/2) × t] / (σ × √t)
d2 = d1 - σ × √t

Call Price = S × N(d1) - K × e^(-rt) × N(d2)
Put  Price = K × e^(-rt) × N(-d2) - S × N(-d1)
```

---

## 四、輸出說明

### 文字報告（Terminal）

每個到期日列出 ATM 合約，包含：

```
到期日: 2025-06-20  (90天後)
ATM 履約價: 210.0
Type   Strike  Mkt Price    Theo     IV%   IV-HV   Delta    Gamma   Theta    Vega     Rho
─────────────────────────────────────────────────────────────────────────────────────────
call   210.0      8.5500   8.3210  28.50%  +5.20  0.5123  0.014200 -0.0821  0.1832  0.0923
put    210.0      7.9200   7.8050  27.80%  +4.50 -0.4877  0.014200 -0.0756  0.1832 -0.0841
```

### 圖表輸出（2 張圖）

**`AAPL_IV_analysis.png`** — IV 分析圖：
- 左：IV Smile（Call，最多 12 個到期日，含 HV30 基準線）
- 右：IV Term Structure（全部到期日，含異常 IV 標示）

**`AAPL_Greeks_analysis.png`** — Greeks 圖：
- 使用者選定的最多 3 個到期日，同時比較：
  - Delta vs Strike
  - Gamma vs Strike
  - Theta vs Strike
  - Vega vs Strike
- 實線 = Call、虛線 = Put
- 金色垂直線 = 現價位置

### CSV 輸出（`AAPL_options_full.csv`）

| 欄位 | 說明 |
|---|---|
| expiration | 到期日 |
| days_to_exp | 距今天數 |
| type | call / put |
| strike | 履約價 |
| market_price | 市場報價 |
| theo_price | BSM 理論價格 |
| IV | 隱含波動率（%） |
| HV_30 | 30日歷史波動率（%） |
| IV_HV_diff | IV - HV 溢價（%） |
| delta / gamma / theta / vega / rho | Greeks |

---

## 五、安裝與執行

### 安裝套件

```bash
# 必裝
pip install yfinance pandas numpy matplotlib scipy

# 建議安裝（計算更快更精準）
pip install py_vollib
```

> 若 `py_vollib` 安裝失敗，程式會自動切換到 `scipy` BSM fallback，功能不受影響。

### 執行

```bash
python options_analyzer.py
```

### 執行流程範例

```
請輸入股票代碼 (例如 AAPL、TSLA、SPY)：AAPL
正在處理 18 個到期日，請稍候...

（文字報告輸出...）

可用到期日（共 18 個）：
  [ 1] 2025-03-28
  [ 2] 2025-04-04
  [ 3] 2025-04-11
  ...

請輸入最多 3 個編號，用逗號分隔
（直接按 Enter 自動選前 3 個）
你的選擇：1,3,6

已選取：['2025-03-28', '2025-04-11', '2025-06-20']
圖表已儲存至 AAPL_IV_analysis.png
圖表已儲存至 AAPL_Greeks_analysis.png
完整資料已儲存至 AAPL_options_full.csv
```

---

## 六、注意事項

- **資料延遲**：yfinance 的選擇權資料可能有 15 分鐘延遲
- **HV 計算**：使用過去 30 個交易日的對數報酬標準差，年化後呈現
- **無風險利率**：預設 5%（`r=0.05`），可在 `analyze_options()` 中修改
- **流動性**：市價為 0 或無報價的合約會自動跳過

---

## 七、免責聲明

本工具僅供**學術研究與學習用途**，不構成任何投資建議。
選擇權市場具有高度風險，請自行評估後謹慎操作。
