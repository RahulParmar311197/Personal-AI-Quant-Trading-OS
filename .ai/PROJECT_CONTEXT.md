# Project Context

## Product
Personal AI Quant Trading OS

## Goal
A personal-use quantitative trading system for Indian markets initially, designed to ingest market data, compute technical/market-structure/SMC/ICT/options/context features, research strategies, backtest them, estimate opportunity quality, enforce deterministic risk controls, paper trade, and eventually integrate broker execution.

## Initial scope
Primary market: NSE
Initial instruments: NIFTY, BANKNIFTY and selected liquid F&O instruments.
Initial priority: research → backtest → paper trading → controlled execution.

## Architectural principle
Market Intelligence → Feature Engineering → Regime → Strategy → Decision → Risk → Execution → Learning

## Non-goals for initial V1
- Multi-tenant SaaS
- Uncontrolled autonomous live trading
- Treating an LLM as the direct order authority
- Optimizing for number of indicators rather than evidence quality
