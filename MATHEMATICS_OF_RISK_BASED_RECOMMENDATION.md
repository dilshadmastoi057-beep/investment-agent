# Investment Agent: Mathematics Behind Risk-Based Company Recommendation

## Executive Summary
The system classifies stocks into Low/Medium/High risk portfolios using a **multi-factor risk score** and **dynamic portfolio optimization** based on Modern Portfolio Theory principles.

---

## 1. RISK SCORE CALCULATION (Range: 0.0 to 1.0)

### Formula:
```
RiskScore = 0.45 × BasePref + 0.20 × AgeAdjust + 0.20 × TimeAdjust + 0.10 × IncomeAdjust + GoalAdjust
```

### Components:

#### A. Base Preference (45% weight)
| User Input | Base Value |
|-----------|-----------|
| "Low Risk" | 0.2 |
| "Medium Risk" | 0.5 |
| "High Risk" | 0.8 |

#### B. Age Adjustment (20% weight)
```
AgeAdjust = max(0, min(1, (50 - Age) / 50))
```
- **Younger = Higher risk tolerance** (more time to recover losses)
- Age 25 → 0.5 (neutral)
- Age 35 → 0.3 (lower tolerance)
- Age 50+ → 0 (conservative)

#### C. Time Period Adjustment (20% weight)
```
TimeAdjust = max(0, min(1, InvestmentYears / 10))
```
- **Longer horizon = Higher risk tolerance**
- 2 years → 0.2 (conservative)
- 5 years → 0.5 (moderate)
- 10+ years → 1.0 (aggressive)

#### D. Income Adjustment (10% weight)
```
IncomeAdjust = max(0, min(1, AnnualIncome / 200,000))
```
- **Higher income = Higher risk capacity**
- $50,000 → 0.25
- $150,000 → 0.75
- $200,000+ → 1.0

#### E. Financial Goals (Bonus)
```
GoalAdjust = 0.15 if "growth" or "wealth" mentioned, else 0
```
- Growth-oriented goals add +0.15 to score

### Risk Level Classification:
```
RiskScore < 0.35  →  LOW RISK
0.35 ≤ RiskScore < 0.70  →  MEDIUM RISK
RiskScore ≥ 0.70  →  HIGH RISK
```

### Example Calculation:
**Profile:** Age 30, Income $60,000, 5-year horizon, Medium risk preference, Growth goals
```
BasePref = 0.5
AgeAdjust = (50-30)/50 = 0.4
TimeAdjust = 5/10 = 0.5
IncomeAdjust = 60,000/200,000 = 0.3
GoalAdjust = 0.15

RiskScore = 0.45(0.5) + 0.20(0.4) + 0.20(0.5) + 0.10(0.3) + 0.15
          = 0.225 + 0.08 + 0.10 + 0.03 + 0.15
          = 0.585  →  MEDIUM RISK ✓
```

---

## 2. COMPANY RANKING: PORTFOLIO OPTIMIZATION

### Step 1: Calculate Stock Performance Metrics
For each stock in the KSE-100 database:

```
Expected_Return = Mean of daily returns (from historical data)
Volatility = Standard Deviation of daily returns
Drawdown = Maximum peak-to-trough decline percentage
Beta = Market sensitivity (Covariance / Market Variance)
```

### Step 2: Compute Risk-Adjusted Score per Stock
```
StockScore = (ExpReturn × Weight_Return) 
           - (Volatility × Weight_Vol) 
           - (Drawdown × Weight_DD)
```

Where weights depend on risk profile:

#### For LOW RISK (RiskScore < 0.35):
```
StockScore = ExpReturn × (0.6 + 0.2)     [Weight: 0.8]
           - Volatility × (1.6 - 0.12)    [Weight: 1.48]
           - Drawdown × (1.1 - 0.175)     [Weight: 0.925]
```
→ **Heavily penalizes volatile stocks**, favors stable returns

#### For MEDIUM RISK (0.35 ≤ RiskScore < 0.70):
```
StockScore = ExpReturn × (0.6 + 0.35)    [Weight: 0.95]
           - Volatility × (1.6 - 0.21)    [Weight: 1.39]
           - Drawdown × (1.1 - 0.275)     [Weight: 0.825]
```
→ **Balanced between growth and safety**

#### For HIGH RISK (RiskScore ≥ 0.70):
```
StockScore = ExpReturn × (0.6 + 0.8)     [Weight: 1.4]
           - Volatility × (1.6 - 0.48)    [Weight: 1.12]
           - Drawdown × (1.1 - 0.35)      [Weight: 0.75]
```
→ **Prioritizes returns, accepts volatility**

### Step 3: Softmax Allocation (Exponential Distribution)

After computing scores, convert to portfolio weights using **softmax with temperature scaling**:

```
Temperature = 0.6 - (RiskScore × 0.4)
```

- LOW RISK:    Temperature = 0.52 (more concentrated)
- MEDIUM RISK: Temperature = 0.4  (balanced)
- HIGH RISK:   Temperature = 0.28 (most concentrated on top performers)

For each stock:
```
Weight_i = exp(Score_i / Temperature) / Sum(exp(Score_j / Temperature))
```

This is the **softmax function** - converts scores to probabilities that sum to 1.0

### Example Allocation (3 stocks):

**Scenario: MEDIUM RISK Portfolio**
| Stock | Score | exp(Score/0.4) | Weight |
|-------|-------|:------:|--------|
| ABL | 0.85 | 2.34 | 23.4% |
| MCB | 0.72 | 1.82 | 18.2% |
| HBL | 0.65 | 1.52 | 15.2% |
| ... (others) | ... | ... | 43.2% |

→ **Top performers get higher allocations, but all get exposure**

---

## 3. RECOMMENDATION RULES

### Action Assignment
```
Sorted by Allocation (highest first):

Top 15% of stocks (by risk & allocation)  →  BUY (strong recommendation)
Next 35% of stocks                         →  HOLD (monitor position)
Remaining 50% of stocks                    →  AVOID (insufficient allocation)
```

### Risk-Adjusted Thresholds:
- **HIGH RISK:** Buy cutoff = 15% of stocks
- **MEDIUM/LOW RISK:** Buy cutoff = 10% of stocks

This ensures HIGH RISK portfolios are more concentrated, while CONSERVATIVE portfolios are more diversified.

---

## 4. PORTFOLIO METRICS

### Expected Annual Return
```
PortfolioReturn = Sum(Stock_Return × Stock_Weight) × 252 trading days × 100%
```

### Portfolio Volatility (Risk)
```
PortfolioVol = Sum(Stock_Volatility × Stock_Weight) × sqrt(252) × 100%
```

### Sharpe Ratio (Risk-Adjusted Performance)
```
SharpeRatio = (PortfolioReturn - RiskFreeRate) / PortfolioVol
            = (PortfolioReturn - 5%) / PortfolioVol
```
- **Sharpe > 1.0** = Good risk-adjusted returns
- **Sharpe > 2.0** = Excellent portfolio

---

## 5. COMPLETE EXAMPLE: How Companies are Selected

**User Profile:**
```
Age: 28, Income: $75,000, Investment Period: 6 years
Risk Preference: Medium, Goal: "Wealth Growth"
```

**Step 1: Calculate Risk Score**
```
RiskScore = 0.45(0.5) + 0.20(0.44) + 0.20(0.6) + 0.10(0.375) + 0.15
          = 0.225 + 0.088 + 0.12 + 0.0375 + 0.15
          = 0.62  →  MEDIUM RISK
```

**Step 2: Get Historical Stock Performance**
| Stock | Return (%) | Volatility (%) | Drawdown (%) |
|-------|------------|:------:|-----------|
| ABL | 0.12 | 2.5 | 8.2 |
| MCB | 0.15 | 3.1 | 10.5 |
| HBL | 0.09 | 2.2 | 6.8 |

**Step 3: Calculate Risk-Adjusted Scores**
```
For RiskScore=0.62:
- RetWeight = 0.6 + 0.62 = 1.22
- VolWeight = 1.6 - 0.372 = 1.228
- DDWeight = 1.1 - 0.31 = 0.79

ABL Score = 0.0012(1.22) - 0.025(1.228) - 0.082(0.79) = 0.00146 - 0.0307 - 0.0648 = -0.0941
MCB Score = 0.0015(1.22) - 0.031(1.228) - 0.105(0.79) = 0.00183 - 0.0381 - 0.0830 = -0.1193
HBL Score = 0.0009(1.22) - 0.022(1.228) - 0.068(0.79) = 0.00110 - 0.0270 - 0.0537 = -0.0796
```

**Step 4: Softmax Allocation** (Temperature = 0.4)
```
ABL: exp(-0.0941/0.4) = exp(-0.235) = 0.791  →  Weight = 36.6%  →  BUY ✓
HBL: exp(-0.0796/0.4) = exp(-0.199) = 0.819  →  Weight = 37.8%  →  BUY ✓
MCB: exp(-0.1193/0.4) = exp(-0.298) = 0.742  →  Weight = 25.6%  →  HOLD
```

**Result:** ABL & HBL recommended as top allocation, MCB as secondary holding.

---

## 6. KEY MATHEMATICAL PRINCIPLES

| Principle | Formula | Purpose |
|-----------|---------|---------|
| **Modern Portfolio Theory** | Return-Volatility Tradeoff | Optimize risk-return ratio |
| **Beta** | Cov(Stock, Market) / Var(Market) | Measure systematic risk |
| **Sharpe Ratio** | (Return - RiskFree) / Volatility | Risk-adjusted performance |
| **Softmax Distribution** | exp(x_i) / Σexp(x_j) | Convert scores to probabilities |
| **Value at Risk (95%)** | Mean - 1.65 × StdDev | Downside risk estimation |

---

## 7. MATHEMATICAL ADVANTAGES

✅ **Risk Profile Customization** - Each user gets unique weights based on 5 factors
✅ **Volatility Penalty** - High-risk stocks weighted down appropriately for conservative portfolios
✅ **Diversification** - Softmax ensures exposure across multiple stocks (not just 1-2)
✅ **Statistical Foundation** - Uses standard finance metrics (Sharpe, Beta, Drawdown)
✅ **Scalability** - Works with any number of stocks in the database

---

## Python Implementation Reference

See `main.py`:
- `_risk_score()` → Lines 77-91 (Risk Score Calculation)
- `_optimize_portfolio()` → Lines 194-227 (Stock Scoring & Allocation)
- `recommend_portfolio()` → Lines 239-340 (Complete recommendation logic)
- `_beta()` → Lines 157-170 (Beta calculation)
- `_market_returns()` → Lines 140-155 (Market return computation)
