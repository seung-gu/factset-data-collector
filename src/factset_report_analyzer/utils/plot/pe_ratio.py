"""P/E ratio plotting utilities."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

from ...analysis.sp500 import SP500
from .time_series import plot_time_series


def plot_pe_ratio_with_price(
    output_path: Path | None = None,
    std_threshold: float = 1.5,
    figsize: tuple[int, int] = (14, 12)
) -> None:
    """Plot S&P 500 Price with P/E Ratios, highlighting periods outside ±σ range.
    
    Creates a two-panel plot showing:
    - Top panel: S&P 500 Price with Trailing P/E Ratio (Q(-4)+Q(-3)+Q(-2)+Q(-1))
    - Bottom panel: S&P 500 Price with Forward P/E Ratio (Q(0)+Q(1)+Q(2)+Q(3))
    
    Periods where P/E ratios are outside the ±σ range are highlighted with
    colored backgrounds (red for above, blue for below).
    
    Args:
        output_path: Path to save the plot. If None, displays the plot.
                     Default: None
        std_threshold: Standard deviation threshold for highlighting outliers.
                       Default: 1.5
        figsize: Figure size in inches (width, height). Default: (14, 12)
    
    Returns:
        None
    
    Example:
        >>> from factset_report_analyzer.utils.plot import plot_pe_ratio_with_price
        >>> from pathlib import Path
        >>> 
        >>> # Save plot to file
        >>> plot_pe_ratio_with_price(
        ...     output_path=Path("output/pe_ratio_plot.png"),
        ...     std_threshold=1.5,
        ...     figsize=(14, 12)
        ... )
        >>> 
        >>> # Or display interactively
        >>> plot_pe_ratio_with_price()
    """
    sp500 = SP500()
    type_labels = {'trailing': 'Q(-4)+Q(-3)+Q(-2)+Q(-1)', 'forward': 'Q(0)+Q(1)+Q(2)+Q(3)'}
    type_colors = {'trailing': 'green', 'forward': 'red'}
    
    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)
    fig.suptitle(f'S&P 500 Price with P/E Ratios (Last Updated: {datetime.now().strftime("%Y-%m-%d")})',
                 fontsize=16, fontweight='bold', y=0.995)
    
    for idx, pe_type in enumerate(['trailing', 'forward']):
        sp500.set_type(pe_type)
        df = sp500.pe_ratio.sort_values('Date')
        if df.empty:
            continue
        
        dates = df['Date']
        prices = df['Price']
        pe_ratios = df['PE_Ratio']
        
        # Use plot_time_series for each subplot
        plot_time_series(dates, [prices, pe_ratios], sigma=std_threshold, sigma_index=1,
                        labels=['S&P 500 Price', f"{pe_type.capitalize()} P/E Ratio"],
                        colors=['black', type_colors[pe_type]], ax=axes[idx])
        axes[idx].set_title(f'S&P 500 Price with {pe_type.capitalize()}({type_labels[pe_type]}) P/E Ratio', fontsize=12, fontweight='bold')
    
    axes[-1].set_xlabel('Date', fontsize=11, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ Plot saved to {output_path}")
    else:
        plt.show()
    plt.close()

