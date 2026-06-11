---
name: strategy-research
description: Turning trading ideas, papers, videos, or indicators into research briefs the Quant Brain pipeline can accept. Use this skill whenever Grover shares a strategy idea, a paper, a MoonDev video/repo, a TradingView screenshot, or asks "could we trade X" — BEFORE writing any strategy code, and instead of jumping straight to implementation.
---

# Strategy Research

## The rule that prevents most curve-fitting
No code until a **research brief** exists with **falsification criteria written first** ("kill this if…"). If the idea can't state what would prove it wrong, it's not ready. Push back politely and produce the brief instead of the bot.

## Brief contents (vault template: `06_Templates/T - Research Brief.md`)
1. One-sentence testable hypothesis
2. **Who loses money to this and why do they keep doing it** — if unanswerable, the "edge" is probably noise
3. Edge type → decay mode: structural (competition compresses) / behavioral (slow, regime-dependent) / informational (fast — lead-lag leadership migrates between venues) / statistical (regime-fragile)
4. Exact v1 rules — **max ~4 conditions**; more conditions = more degrees of freedom = harder gauntlet
5. Named real data files (or an acquisition plan via the market-data skill)
6. Falsification criteria
7. Triage score: edge/data/capacity/complexity 1–10, avg ≥6 to proceed

## Source handling
- **Papers**: extract claims → translate to "so what for our markets/timeframes" → check method transfer (e.g., seconds-scale lead-lag needs trade-level data + Hayashi-Yoshida-style estimation, NOT correlations on our candle CSVs).
- **MoonDev / YouTube / Twitter**: treat every claimed result as unverified `idea`. Re-derive on our data; never port claimed performance numbers into a brief as evidence.
- **Indicator screenshots**: transcribe rules exactly, then ask which conditions are load-bearing vs decoration before coding.
- **Borrowed feature lists** ("another AI suggested these 10 things"): each item gets its own triage score. Never integrate a batch wholesale.

## Anti-patterns to actively resist
- Indicator soup (stacking filters until the curve fits)
- Paper-worship (2018 equities result ≠ 2026 crypto edge)
- Starting a new app/repo for an idea TickerTape could host — flag it, point at the Decision Log

## Output
A filled brief + honest triage score + the single cheapest test that could kill the idea fast. That's the deliverable — not code.
