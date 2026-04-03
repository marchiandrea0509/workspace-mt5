# Trade Plan Deep Dive — ETH_PERP

Generated: 2026-03-23T13:21:44+01:00 | UTC: 2026-03-23T12:21:44Z

## Snapshot

- Direction: **SHORT**
- Trade type: **SHORT_CONTINUATION**
- Quality: **LOW** (rank #17)
- Screening score: **57.50** (best rank #19)
- Risk bucket: **LOW**
- Trade candidate: **NO**

## A) Table 1 — Key Levels

| Type | Level | Price | Notes |
| --- | --- | --- | --- |
| SUPPORT | S4 | 2052.6104 | ATR pullback objective |
| SUPPORT | S1 | 1908.9400 | 4h pivot support |
| SUPPORT | S2 | 1797.0000 | 1d pivot support |
| RESISTANCE | R3 | 2193.3696 | ATR stretch objective |
| RESISTANCE | R1 | 2385.0000 | 4h pivot resistance |
| RESISTANCE | R4 | 2394.1241 | buffered disaster SL |

## B) Table 2 — Scenarios

| Scenario | Probability | Expected move | Triggers |
| --- | --- | --- | --- |
| Bearish follow-through / lower reset | 60% | 3.76% | Lose 2137.0659 and fail to reclaim the 4h reaction zone. |
| Squeeze / continuation higher | 40% | 10.08% | Accept back above 2385.0000 or invalidate the fade structure. |

## Market state

- 4h trend/side: **NEUTRAL / NEUTRAL**
- 1d trend/side: **NEUTRAL / SHORT**
- Volatility regime: **HIGH**
- ADX regime: **TRENDING**

## Macro / news / fundamental context

- Official macro bias: **MIXED**
- Macro alignment: **UNFAVORABLE**
- Headline pressure: **MIXED**
- Event risk 24h / 72h: **LOW / MEDIUM**
- Sentiment state: **EXTREME_FEAR**
- Fundamental availability: **PROXY_ONLY**
- Fundamental note: Macro/flows/news context is available; classic corporate fundamentals are not applicable or not wired.
- Context note: Macro alignment is unfavorable; headline pressure is mixed; event risk in the next 24h is low; crypto sentiment is extreme fear.

Top headlines:
- Crypto market rattled by $400 million liquidations as bitcoin dips to $68,000: Crypto Markets Today - CoinDesk
- Nasdaq Seeks to Build Crypto Into Wall Street’s Market Plumbing - Bloomberg.com
- Stock Market Crash: The Best Cryptocurrencies to Buy Right Now - The Motley Fool
- Crypto Weekly Digest | BTC Hits $76K Then Retreats as SEC Declares Major Tokens Not Securities - Moomoo
- The end of shadow trading? Russia’s forthcoming crypto-market rules - ForkLog

Scheduled macro events:
- 2026-03-25T08:30:00Z — U.S. International Transactions and Investment Position, 4th Quarter and Year 2025 (NEWS)
- 2026-04-02T08:30:00Z — U.S. International Trade in Goods and Services, February 2026 (NEWS)
- 2026-04-09T08:30:00Z — GDP (Third Estimate), Industries, Corporate Profits, State GDP, and State Personal Income, 4th Quarter and Year 2025 (NEWS)
- 2026-04-09T08:30:00Z — Personal Income and Outlays, February 2026 (NEWS)
- 2026-04-30T08:30:00Z — GDP (Advance Estimate), 1st Quarter 2026 (NEWS)

## C) Table 3 — Orders

| Level | Type | Price | Size % | Margin USDT | Lev | SL | TP1 / TP2 | Trail trigger / dist |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | LIMIT | 2137.0659 | 37.20 | 166.27 | 2.00 | 2394.1241 | 2094.8382 / 2043.2265 | 2094.8382 / 23.4599 |
| L2 | LIMIT | 2155.8338 | 35.42 | 158.32 | 2.00 | 2394.1241 | 2113.6061 / 2061.9944 | 2113.6061 / 23.4599 |
| L3 | LIMIT | 2172.2557 | 27.38 | 122.38 | 2.00 | 2394.1241 | 2130.0280 / 2078.4163 | 2130.0280 / 23.4599 |

## D) Peak Risk Score

- **LOW** — Normal sizing is acceptable if the structure remains intact.
- No major stress flags fired; use normal structure discipline.

## E) Risk Summary

- RiskBudgetUSDT: **100.00**
- EstimatedLossUSDT: **100.00**
- EstimatedLoss%Equity: **n/a%**
- Pass/Fail vs risk budget: **YES**
- Estimated average entry: **2153.3488**
- Margin used % of free margin: **44.70%**

## F) 5-line Do this now

- Check whether price is near the first planned order at 2137.0659 before placing the setup.
- Use the disaster SL at 2394.1241 and do not tighten it just to fit size.
- Keep total risk at or below 100.00 USDT.
- Start with the primary method (SELL_RALLY); backup is BREAKDOWN.
- If event risk stays LOW, keep leverage <= x5 and avoid chasing.

## Final trade setup table

| Symbol | Dir | Trade type | Score | Rank | Quality | Risk | Entry zone | Avg entry | SL | TP1 | TP2 | Margin | Risk USDT | Risk %Eq | RiskFrac | Pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ETH_PERP | SHORT | SHORT_CONTINUATION | 57.50 | 19 | LOW | LOW | 2137.0659 → 2172.2557 | 2153.3488 | 2394.1241 | 2094.8382 | 2043.2265 | 446.97 | 100.00 | n/a% | 1.00 | YES |

## Notes

- Preferred execution style overrides screener-implied style (BREAKDOWN -> SELL_RALLY).
- Continuation setup has insufficient projected reward-to-risk.
- Macro alignment is unfavorable; headline pressure is mixed; event risk in the next 24h is low; crypto sentiment is extreme fear.
