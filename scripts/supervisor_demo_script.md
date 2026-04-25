# Supervisor Demo Script (2-3 Minutes)

## Opening
Today I am presenting the updated investment-agent system with a research-first workflow.
Instead of relying on paid market APIs, we use structured equity research reports plus risk-based portfolio math.

## Problem and Constraint
Paid and licensed real-time feeds are costly for student projects.
So we implemented a low-cost architecture where recommendations can be generated using:
1) historical market data already in our system
2) manually prepared equity research reports for top KSE companies

## What Is New
We added a dedicated Equity Research module with:
1) report upload endpoint (`/equity-reports/upload`)
2) report retrieval endpoints (`/equity-reports` and `/equity-reports/{symbol}`)
3) fundamental scoring integration in recommendation logic
4) fallback behavior when no report exists

## Live Demo Flow
1) Open dashboard and show Equity Research Reports section.
2) Upload `equity_reports.json`.
3) Show loaded company reports with company name, sector, FA Score, target view, and confidence.
4) Run recommendation.
5) Show recommendation table now includes FA Score and Report View.

## Technical Value
Recommendation now combines:
1) expected return, volatility, drawdown, beta from market history
2) fundamental report score (growth, profitability, leverage, valuation, margins)
3) high-confidence research overrides action when justified

## Academic and Industry Relevance
This design is explainable, low-cost, and practical for FYP constraints.
It can later be upgraded with licensed feeds without redesigning the core engine.

## Closing
Current milestone: research-first engine is fully working end-to-end.
Next milestone: expand reports to more KSE-100 companies and improve validation with backtesting.
