# ⚡ Autonomous Alpha: Algorithmic & AI-Driven Quantitative Trading System

> An end-to-end quantitative trading infrastructure bridging native MetaTrader 5 execution with algorithmic signal generation and multi-agent AI reasoning.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MetaTrader 5](https://img.shields.io/badge/MetaTrader_5-IPC_Bridge-blue?style=for-the-badge)
![Pandas](https://img.shields.io/badge/Pandas-Vectorized_Analytics-150458?style=for-the-badge&logo=pandas&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

## 📌 Project Overview

This repository documents the architecture, mathematical formulations, and software pipeline for building a high-speed, systematic algorithmic trading system. 

By treating the **MetaTrader 5 (MT5)** client strictly as an ultra-reliable broker gateway and liquidity provider interface, the execution engine decouples algorithmic computation and AI inference into a standalone Python runtime.


┌─────────────────────────────────┐       IPC / Win32       ┌────────────────────────────────┐
│   Python Strategy & AI Core     │ ◄─────────────────────► │     MetaTrader 5 Terminal      │
│  - Indicator Pipeline (Pandas)  │    Tick / Bar Data      │  - Order Execution Engine      │
│  - AI Sentiment / LLM Agents    │                         │  - Broker Liquidity Gateway    │
│  - Dynamic Risk Guardian        │   Trade Requests / Deals│  - Real-Time Position Monitor  │
└─────────────────────────────────┘                         └────────────────────────────────┘



## 🚀 Key Modules Built

- **Native Terminal Bridge**: High-throughput communication layer linking Python's runtime directly to the MT5 desktop client over Windows IPC hooks.
- **Tick Stream Event Loop**: Custom tick-polling event architecture simulating real-time market subscriptions (`OnTick`) with zero external API latency.
- **Vectorized Technical Engine**: Dynamic sliding-window calculations (SMA, EMA, ATR, RSI) processed directly via Pandas dataframes from raw candlestick arrays.
- **Automated Order Dispatch**: Deterministic order routing supporting Fill-or-Kill (FOK) and Immediate-or-Cancel (IOC) fills, automatic slippage tolerance, and automated Stop-Loss / Take-Profit (SL/TP) math.
- **State & Risk Management Engine**: Position verification filters that isolate algorithmic orders via `Magic Numbers` to eliminate cross-talk with manual positions.

---

## 🛠 Tech Stack

- **Runtime & Execution**: Python 3.11+ on Windows 10
- **Trading API**: `MetaTrader5` native Win32 library
- **Quantitative Analytics**: Pandas, NumPy
- **Development & IDE**: Visual Studio Code, Git

---

## 📂 Repository Structure

```plaintext
├── core/
│   ├── connection.py        # MT5 initialization & session teardown
│   ├── data_feed.py         # Bar and tick streaming handlers
│   └── execution.py         # Order dispatch and position management
├── strategies/
│   ├── ma_crossover.py      # Moving average trend and momentum models
│   └── price_action.py      # Delta movement & threshold breach monitors
├── config.py                # Symbol registry, lot sizing, and risk parameters
├── requirements.txt         # Project dependencies
└── README.md
