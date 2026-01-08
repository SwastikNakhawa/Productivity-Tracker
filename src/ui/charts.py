"""
Chart helpers for the analytics dashboard.
Uses matplotlib to generate figures from activity data.
"""
from datetime import datetime
from typing import List, Dict

import matplotlib

# Use non-interactive backend (required for embedding in Tk)
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import numpy as np  # noqa: E402


def _empty_figure(message: str = "No data available"):
    """Return a simple figure with a centered message."""
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12)
    ax.axis("off")
    fig.tight_layout()
    return fig


def _prepare_dataframe(activities: List[Dict]) -> pd.DataFrame:
    """Normalize activities list into a DataFrame with useful columns."""
    if not activities:
        return pd.DataFrame()

    df = pd.DataFrame(activities)
    if "start_time" in df.columns:
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    else:
        df["start_time"] = pd.to_datetime(datetime.now())

    df["date"] = df["start_time"].dt.date
    df["hour"] = df["start_time"].dt.hour
    df["productivity_score"] = pd.to_numeric(df.get("productivity_score", 50), errors="coerce").fillna(50)
    df["duration"] = pd.to_numeric(df.get("duration", 0), errors="coerce").fillna(0)
    df["category"] = df.get("category", "unknown").fillna("unknown")
    return df


def _productivity_trend(df: pd.DataFrame):
    """Line chart of average productivity per day."""
    if df.empty:
        return _empty_figure()

    trend = df.groupby("date")["productivity_score"].mean()
    fig, ax = plt.subplots(figsize=(5.5, 3))
    ax.plot(trend.index, trend.values, marker="o", color="#2b8cd6")
    ax.set_title("Productivity Score by Day")
    ax.set_ylabel("Score (0-100)")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def _category_distribution(df: pd.DataFrame):
    """Horizontal bar chart of time spent per category."""
    if df.empty:
        return _empty_figure()

    category_time = df.groupby("category")["duration"].sum().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    hours = category_time / 3600
    ax.barh(category_time.index, hours, color="#4caf50")
    ax.set_title("Time Spent by Category (hours)")
    ax.set_xlabel("Hours")
    for i, v in enumerate(hours):
        ax.text(v + 0.05, i, f"{v:.1f}h", va="center", fontsize=9)
    fig.tight_layout()
    return fig


def _hourly_heatmap(df: pd.DataFrame):
    """Heatmap of average productivity score by hour."""
    if df.empty:
        return _empty_figure()

    pivot = df.pivot_table(index="hour", values="productivity_score", aggfunc="mean").reindex(range(24))
    # Use fillna with forward and backward fill (updated pandas syntax)
    pivot_filled = pivot.ffill().bfill().fillna(50)

    fig, ax = plt.subplots(figsize=(5.5, 3))
    data = pivot_filled.values.reshape(-1, 1)
    im = ax.imshow(data, aspect="auto", cmap="YlGnBu", vmin=0, vmax=100)
    ax.set_yticks(range(24))
    ax.set_yticklabels(range(24))
    ax.set_xticks([])
    ax.set_title("Productivity by Hour of Day")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Score")
    fig.tight_layout()
    return fig


def create_charts(activities: List[Dict]) -> List[plt.Figure]:
    """
    Build a set of matplotlib figures from activity data.
    Returns a list of figures to embed in the GUI.
    """
    df = _prepare_dataframe(activities)
    if df.empty:
        return [_empty_figure()]

    figures = [
        _productivity_trend(df),
        _category_distribution(df),
        _hourly_heatmap(df)
    ]
    return figures
