import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

from app.config import Config

os.makedirs(Config.CHART_DIR, exist_ok=True)


def generate_candlestick_chart(df, stock_code, stock_name=""):
    if df is None or df.empty:
        return None

    chart_config = {
        "type": "candle",
        "style": "charles",
        "title": f"{stock_code} - {stock_name}",
        "ylabel": "Price (IDR)",
        "volume": True,
        "ylabel_lower": "Volume",
        "figsize": (12, 8),
        "panel_ratios": (3, 1),
        "returnfig": True,
    }

    extra_plots = []

    # MA lines
    if "MA20" in df.columns and pd.notna(df["MA20"]).any():
        extra_plots.append(
            mpf.make_addplot(df["MA20"], color="orange", width=0.8, label="MA20")
        )
    if "MA50" in df.columns and pd.notna(df["MA50"]).any():
        extra_plots.append(
            mpf.make_addplot(df["MA50"], color="blue", width=0.8, label="MA50")
        )

    fig, axes = mpf.plot(df, **chart_config, addplot=extra_plots)

    filename = f"{stock_code.replace('.JK', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(Config.CHART_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", dpi=100)
    plt.close(fig)

    return filepath


def generate_rsi_chart(df, stock_code):
    if df is None or df.empty or "RSI" not in df.columns:
        return None

    fig, ax = plt.subplots(figsize=(12, 3))
    ax.plot(df.index, df["RSI"], color="purple", linewidth=1.5, label="RSI")
    ax.axhline(y=70, color="r", linestyle="--", alpha=0.5, label="Overbought (70)")
    ax.axhline(y=30, color="g", linestyle="--", alpha=0.5, label="Oversold (30)")
    ax.axhline(y=50, color="gray", linestyle="--", alpha=0.3)
    ax.fill_between(df.index, 30, 70, alpha=0.1, color="gray")
    ax.set_title(f"RSI - {stock_code}")
    ax.set_ylabel("RSI")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    filename = f"rsi_{stock_code.replace('.JK', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(Config.CHART_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", dpi=100)
    plt.close(fig)

    return filepath


def generate_macd_chart(df, stock_code):
    if df is None or df.empty or "MACD" not in df.columns:
        return None

    fig, ax = plt.subplots(figsize=(12, 3))
    ax.plot(df.index, df["MACD"], color="blue", linewidth=1.5, label="MACD")
    ax.plot(df.index, df["MACD_Signal"], color="red", linewidth=1.5, label="Signal")
    colors = ["g" if v >= 0 else "r" for v in df["MACD_Hist"]]
    ax.bar(df.index, df["MACD_Hist"], color=colors, alpha=0.5, label="Histogram", width=1)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.3)
    ax.set_title(f"MACD - {stock_code}")
    ax.set_ylabel("MACD")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    filename = f"macd_{stock_code.replace('.JK', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(Config.CHART_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", dpi=100)
    plt.close(fig)

    return filepath


def generate_full_analysis_chart(df, stock_code, stock_name=""):
    if df is None or df.empty:
        return None

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.3)

    # Candlestick
    ax1 = fig.add_subplot(gs[0])
    _plot_candlestick(ax1, df, stock_code, stock_name)
    ax1.set_ylabel("Price (IDR)")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper left")

    # Volume
    ax2 = fig.add_subplot(gs[1])
    colors = ["g" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "r" for i in range(len(df))]
    ax2.bar(df.index, df["Volume"], color=colors, alpha=0.6, width=1)
    if "Volume_MA" in df.columns:
        ax2.plot(df.index, df["Volume_MA"], color="orange", linewidth=1, label="Volume MA")
    ax2.set_ylabel("Volume")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper left")

    # RSI
    ax3 = fig.add_subplot(gs[2])
    if "RSI" in df.columns:
        ax3.plot(df.index, df["RSI"], color="purple", linewidth=1.5)
        ax3.axhline(y=70, color="r", linestyle="--", alpha=0.5)
        ax3.axhline(y=30, color="g", linestyle="--", alpha=0.5)
        ax3.fill_between(df.index, 30, 70, alpha=0.1, color="gray")
    ax3.set_ylabel("RSI")
    ax3.set_ylim(0, 100)
    ax3.grid(True, alpha=0.3)

    # MACD
    ax4 = fig.add_subplot(gs[3])
    if "MACD" in df.columns:
        ax4.plot(df.index, df["MACD"], color="blue", linewidth=1.5, label="MACD")
        ax4.plot(df.index, df["MACD_Signal"], color="red", linewidth=1.5, label="Signal")
        bar_colors = ["g" if v >= 0 else "r" for v in df["MACD_Hist"]]
        ax4.bar(df.index, df["MACD_Hist"], color=bar_colors, alpha=0.5, width=1)
        ax4.axhline(y=0, color="gray", linestyle="--", alpha=0.3)
    ax4.set_ylabel("MACD")
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc="upper left")

    fig.suptitle(f"{stock_code} - {stock_name}", fontsize=14, fontweight="bold", y=0.98)

    filename = f"full_{stock_code.replace('.JK', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(Config.CHART_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", dpi=100)
    plt.close(fig)

    return filepath


def _plot_candlestick(ax, df, stock_code, stock_name):
    up = df[df["Close"] >= df["Open"]]
    down = df[df["Close"] < df["Open"]]

    width = 0.6
    width2 = 0.05

    ax.bar(up.index, up["Close"] - up["Open"], width, bottom=up["Open"], color="g", edgecolor="g")
    ax.bar(up.index, up["High"] - up["Close"], width2, bottom=up["Close"], color="g")
    ax.bar(up.index, up["Low"] - up["Open"], width2, bottom=up["Open"], color="g")

    ax.bar(down.index, down["Close"] - down["Open"], width, bottom=down["Open"], color="r", edgecolor="r")
    ax.bar(down.index, down["High"] - down["Open"], width2, bottom=down["Open"], color="r")
    ax.bar(down.index, down["Low"] - down["Close"], width2, bottom=down["Close"], color="r")

    if "MA20" in df.columns:
        ax.plot(df.index, df["MA20"], color="orange", linewidth=1, label="MA20")
    if "MA50" in df.columns:
        ax.plot(df.index, df["MA50"], color="blue", linewidth=1, label="MA50")

    ax.set_title(f"{stock_code} - {stock_name}")
