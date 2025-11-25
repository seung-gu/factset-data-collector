"""Time series plotting utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


def plot_time_series(
    dates: pd.Series,
    values: pd.Series | list[pd.Series],
    sigma: float | None = None,
    sigma_index: int = 0,
    output_path: Path | None = None,
    figsize: tuple[int, int] = (14, 8),
    labels: list[str] | None = None,
    colors: list[str] | None = None,
    ax: plt.Axes | None = None
) -> None:
    """Plot time series data with optional sigma threshold highlighting.
    
    This function creates time series plots with support for single or dual-axis
    plotting (up to 2 series). It can optionally highlight periods where values
    are outside a specified standard deviation threshold.
    
    Args:
        dates: Date series for x-axis (pandas Series with datetime values)
        values: Single pandas Series or list of up to 2 Series to plot
        sigma: Standard deviation threshold for highlighting outliers. If None,
               no highlighting is applied. Default: None
        sigma_index: Index of series to apply sigma threshold to (0 or 1).
                     Only used when sigma is not None. Default: 0
        output_path: Path to save the plot. If None, displays the plot.
                     Default: None
        figsize: Figure size in inches (width, height). Default: (14, 8)
        labels: Labels for each series. If None, auto-generated from series names.
                Default: None
        colors: Colors for each series. If None, uses ['blue', 'red'].
                Default: None
        ax: Existing matplotlib Axes to plot on. If None, creates new figure.
            Default: None
    
    Returns:
        None
    
    Raises:
        ValueError: If more than 2 value series are provided
    
    Example:
        >>> from factset_report_analyzer import SP500
        >>> from factset_report_analyzer.utils.plot import plot_time_series
        >>> from pathlib import Path
        >>> 
        >>> sp500 = SP500()
        >>> sp500.set_type('trailing')
        >>> pe_df = sp500.pe_ratio.sort_values('Date')
        >>> 
        >>> # Single series with sigma highlighting
        >>> plot_time_series(
        ...     dates=pe_df['Date'],
        ...     values=pe_df['PE_Ratio'],
        ...     sigma=1.5,
        ...     labels=['Trailing P/E Ratio'],
        ...     output_path=Path("output/pe_ratio.png")
        ... )
        >>> 
        >>> # Dual axis plot
        >>> plot_time_series(
        ...     dates=pe_df['Date'],
        ...     values=[pe_df['Price'], pe_df['PE_Ratio']],
        ...     sigma=1.5,
        ...     sigma_index=1,
        ...     labels=['S&P 500 Price', 'P/E Ratio'],
        ...     colors=['black', 'green']
        ... )
    """
    values = [values] if isinstance(values, pd.Series) else values
    if len(values) > 2:
        raise ValueError("Maximum 2 value series allowed")
    
    dates_vals = pd.to_datetime(dates).values
    colors = colors or ['blue', 'red'][:len(values)]
    labels = labels or [v.name if v.name else f'Series {i+1}' for i, v in enumerate(values)]
    
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure
    ax2 = ax.twinx() if len(values) == 2 else None
    
    for i, val in enumerate(values):
        (ax2 if i == 1 else ax).plot(dates_vals, val.values, color=colors[i], linewidth=1.5,
                                     label=labels[i], alpha=0.7, zorder=2)
    
    if sigma is not None and sigma_index < len(values):
        v = values[sigma_index].values
        mean, std = np.mean(v), np.std(v)
        upper, lower = mean + sigma * std, mean - sigma * std
        for mask, color in [(v > upper, 'red'), (v < lower, 'blue')]:
            starts = np.where(np.diff(np.concatenate(([False], mask, [False]))))[0]
            for i in range(0, len(starts), 2):
                if i+1 < len(starts):
                    ax.axvspan(dates_vals[starts[i]], dates_vals[starts[i+1]-1], alpha=0.2, color=color, zorder=0)
        target_ax = ax2 if sigma_index == 1 and ax2 else ax
        for y, style in [(mean, '--'), (upper, ':'), (lower, ':')]:
            target_ax.axhline(y=y, color='gray' if style == '--' else 'gold', linestyle=style, 
                    linewidth=1.2, alpha=0.7, zorder=1)
    
    ax.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax.set_ylabel(labels[0], fontsize=11, fontweight='bold', color=colors[0])
    ax.tick_params(axis='y', labelsize=9, labelcolor=colors[0])
    ax.grid(True, alpha=0.15, linestyle='-', linewidth=0.3)
    if ax2:
        ax2.set_ylabel(labels[1], fontsize=11, fontweight='bold', color=colors[1])
        ax2.tick_params(axis='y', labelsize=9, labelcolor=colors[1])
        ax2.margins(y=0.2)
    
    lines, lbls = ax.get_legend_handles_labels()
    if ax2:
        lines2, lbls2 = ax2.get_legend_handles_labels()
        lines, lbls = lines + lines2, lbls + lbls2
    
    if sigma is not None and sigma_index < len(values):
        v = values[sigma_index].values
        mean, std = np.mean(v), np.std(v)
        upper, lower = mean + sigma * std, mean - sigma * std
        lines.extend([
            plt.Line2D([0], [0], color='gray', linestyle='--', linewidth=1.2, label=f'Mean: {mean:.2f}'),
            plt.Line2D([0], [0], color='gold', linestyle=':', linewidth=1.2, label=f'+{sigma}σ: {upper:.2f}'),
            plt.Line2D([0], [0], color='gold', linestyle=':', linewidth=1.2, label=f'-{sigma}σ: {lower:.2f}'),
            plt.Rectangle((0, 0), 1, 1, facecolor='red', alpha=0.2, label=f'>{sigma}σ'),
            plt.Rectangle((0, 0), 1, 1, facecolor='blue', alpha=0.2, label=f'<-{sigma}σ')
        ])
        lbls.extend([f'Mean: {mean:.2f}', f'+{sigma}σ: {upper:.2f}', f'-{sigma}σ: {lower:.2f}', 
                    f'>{sigma}σ', f'<-{sigma}σ'])
    
    ax.legend(lines, lbls, loc='upper left', fontsize=9, framealpha=0.9, edgecolor='lightgray')
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=9)
    
    if ax is None or output_path:
        plt.tight_layout()
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"✅ Plot saved to {output_path}")
        else:
            plt.show()
        plt.close()

