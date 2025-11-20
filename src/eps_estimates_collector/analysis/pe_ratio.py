"""P/E ratio calculation from EPS estimates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

# Type definitions
PE_RATIO_TYPE = Literal['forward', 'trailing']
import re
import tempfile

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import logging

# Suppress matplotlib font manager warnings
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

from ..utils.csv_storage import read_csv


def _parse_quarter_to_date(quarter_str: str) -> datetime | None:
    """Parse quarter string (e.g., "Q1'14") to datetime.
    
    Args:
        quarter_str: Quarter string like "Q1'14", "Q2'15", etc.
        
    Returns:
        Datetime representing the start of the quarter, or None
    """
    match = re.match(r"Q([1-4])'(\d{2})", quarter_str)
    if not match:
        return None
    
    quarter = int(match.group(1))
    year_short = int(match.group(2))
    
    # Convert 2-digit year to 4-digit year
    # FactSet data starts from 2016, so all quarters are in 2000s
    # Standard conversion: 00-49 -> 2000-2049, 50-99 -> 1950-1999
    # For FactSet data (2014+), we use 2000+ for all cases
    if year_short >= 50:
        # Years 50-99: 1950-1999 (unlikely for FactSet data, but handle for completeness)
        year = 1900 + year_short
    else:
        # Years 00-49: 2000-2049 (covers all FactSet data from 2014+)
        year = 2000 + year_short
    
    # Calculate month (Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct)
    month = (quarter - 1) * 3 + 1
    
    return datetime(year, month, 1)


def _get_quarter_eps_sum(
    row: pd.Series,
    quarter_cols: list[str],
    report_date: datetime,
    type: PE_RATIO_TYPE
) -> float | None:
    """Calculate 4-quarter EPS sum based on type.
    
    Args:
        row: DataFrame row with quarter columns
        quarter_cols: List of quarter column names
        report_date: Report date
        type: Type of EPS calculation:
            - 'forward': Q(0)+Q(1)+Q(2)+Q(3) - Report date quarter and next 3 quarters
            - 'trailing': Q(-4)+Q(-3)+Q(-2)+Q(-1) - Last 4 quarters before report date
        
    Returns:
        4-quarter EPS sum, or None if insufficient data
    """
    # Parse valid quarters with their dates
    quarter_data = [
        {
            'quarter': col,
            'eps': float(str(val).replace('*', '').strip()),
            'date': _parse_quarter_to_date(col)
        }
        for col in quarter_cols
        if (val := row[col]) is not None
        and str(val).strip()
        and (eps_val := float(str(val).replace('*', '').strip())) > 0
        and (q_date := _parse_quarter_to_date(col)) is not None
    ]
    
    if not quarter_data:
        return None
    
    # Sort by date
    quarter_data.sort(key=lambda x: x['date'])
    
    # Find the quarter that report_date belongs to
    # A quarter spans from q['date'] to (but not including) the next quarter's date
    report_quarter = next(
        (
            q
            for q, next_q in zip(quarter_data, quarter_data[1:] + [{'date': datetime.max}])
            if q['date'] <= report_date < next_q['date']
        ),
        quarter_data[-1] if quarter_data[-1]['date'] <= report_date else quarter_data[0]
    )
    
    # Split quarters into before, at, and after report_quarter
    quarters_before = [q for q in quarter_data if q['date'] < report_quarter['date']]
    quarters_after = [q for q in quarter_data if q['date'] > report_quarter['date']]
    
    if type == 'forward':
        # Q(0)+Q(1)+Q(2)+Q(3) - Report date quarter and next 3 quarters
        selected = [report_quarter] + quarters_after[:3]
    elif type == 'trailing':
        # Q(-4)+Q(-3)+Q(-2)+Q(-1) - Last 4 quarters before report date
        selected = quarters_before[-4:]
    else:
        return None
    
    return sum(q['eps'] for q in selected) if len(selected) == 4 else None


def fetch_sp500_pe_ratio(
    type: PE_RATIO_TYPE = 'forward'
) -> pd.DataFrame:
    """Fetch P/E ratios from EPS estimates using S&P 500 prices.
    
    Calculates Price-to-Earnings (P/E) ratios using 4-quarter EPS sums and S&P 500 stock prices.
    EPS is calculated as the sum of 4 quarters based on the type:
    - forward: Q(0)+Q(1)+Q(2)+Q(3) - Report date quarter and next 3 quarters
    - trailing: Q(-4)+Q(-3)+Q(-2)+Q(-1) - Last 4 quarters before report date
    
    Args:
        type: Type of P/E ratio to calculate:
            - 'forward': Q(0)+Q(1)+Q(2)+Q(3) - Report date quarter and next 3 quarters
            - 'trailing': Q(-4)+Q(-3)+Q(-2)+Q(-1) - Last 4 quarters before report date
        
    Returns:
        DataFrame with P/E ratios:
        - Report_Date: Report date
        - Price_Date: Date of price used (most recent price on or before report_date)
        - Price: S&P 500 stock price used
        - EPS_4Q_Sum: 4-quarter EPS sum used for calculation
        - PE_Ratio: Calculated P/E ratio (Price / EPS_4Q_Sum)
        - Type: Type of calculation ('forward', 'trailing-like', or 'mix')
        
    Note:
        Stock prices are matched to the most recent price on or before the report date.
        EPS data is always loaded from public URL.
        S&P 500 (^GSPC) data is automatically loaded from yfinance.
        Requires yfinance package: pip install yfinance or uv add yfinance
    """
    # Auto-load from public URL
    temp_path = Path(tempfile.gettempdir()) / "extracted_estimates.csv"
    df_eps = read_csv("extracted_estimates.csv", temp_path)
    
    if df_eps is None:
        raise FileNotFoundError(
            "CSV file not found in public URL. Please ensure extracted_estimates.csv "
            "exists at https://pub-62707afd3ebb422aae744c63c49d36a0.r2.dev/extracted_estimates.csv"
        )
    
    df_eps['Report_Date'] = pd.to_datetime(df_eps['Report_Date'])
    
    # Determine date range from EPS data (start from min report date, end at today)
    min_date = df_eps['Report_Date'].min()
    start_date = min_date.strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Auto-load S&P 500 price data
    try:
        import yfinance as yf
        print(f"📈 Loading S&P 500 price data from yfinance ({start_date} to {end_date})...")
        sp500 = yf.Ticker('^GSPC')
        hist = sp500.history(start=start_date, end=end_date)
        price_dict = {date.strftime('%Y-%m-%d'): float(close) for date, close in zip(hist.index, hist['Close'])}
        print(f"✅ Loaded {len(price_dict)} S&P 500 price points")
    except ImportError:
        raise ImportError(
            "yfinance is required for automatic S&P 500 price loading. "
            "Install it with: pip install yfinance or uv add yfinance"
        )
    except Exception as e:
        raise Exception(f"Failed to load S&P 500 price data: {e}")
    
    # Convert price_dict to DataFrame
    price_df = pd.DataFrame([
        {'Date': k, 'Price': v} for k, v in price_dict.items()
    ])
    price_df['Date'] = pd.to_datetime(price_df['Date'])
    
    # Get quarter columns
    quarter_cols = [col for col in df_eps.columns if col != 'Report_Date']
    
    # Use only dates that have price data (trading days only)
    df_eps_sorted = df_eps.sort_values('Report_Date')
    
    # Calculate P/E ratios for each price date
    results = []
    
    for _, price_row in price_df.iterrows():
        price_date = price_row['Date']
        price = float(price_row['Price'])
        
        # Find most recent EPS row on or before this price date
        eps_candidates = df_eps_sorted[df_eps_sorted['Report_Date'] <= price_date]
        if eps_candidates.empty:
            continue
        
        # Try reports from most recent to oldest until we find one with exactly 4 quarters
        # Use price_date (current date) as the reference point for quarter calculation
        eps_sum = None
        report_date = None
        for _, eps_row in reversed(list(eps_candidates.iterrows())):
            report_date = eps_row['Report_Date']
            # Use price_date instead of report_date for quarter calculation
            eps_sum = _get_quarter_eps_sum(eps_row, quarter_cols, price_date, type)
            # _get_quarter_eps_sum already checks for exactly 4 quarters
            if eps_sum and eps_sum > 0:
                break
        
        if not eps_sum or eps_sum <= 0:
            continue
        
        pe_ratio = price / eps_sum
        results.append({
            'Report_Date': report_date.strftime('%Y-%m-%d'),
            'Price_Date': price_date.strftime('%Y-%m-%d'),
            'Price': price,
            'EPS_4Q_Sum': eps_sum,
            'PE_Ratio': pe_ratio,
            'Type': type
        })
    
    if not results:
        return pd.DataFrame(columns=['Report_Date', 'Price_Date', 'Price', 'EPS_4Q_Sum', 'PE_Ratio', 'Type'])
    
    df_result = pd.DataFrame(results)
    return df_result


def plot_pe_ratio_with_price(
    output_path: Path | None = None,
    std_threshold: float = 1.5,
    figsize: tuple[int, int] = (14, 12)
) -> None:
    """Plot S&P 500 Price with P/E Ratios, highlighting periods outside ±1.5σ range.
    
    Creates two subplots showing S&P 500 Price alongside different P/E ratio types:
    - Q(-4)+Q(-3)+Q(-2)+Q(-1) (trailing): Last 4 quarters before report date
    - Q(0)+Q(1)+Q(2)+Q(3) (forward): Report date quarter and next 3 quarters
    
    Each subplot highlights periods where P/E ratio is outside ±1.5σ range:
    - Red bands: P/E > +1.5σ (overvalued periods)
    - Blue bands: P/E < -1.5σ (undervalued periods)
    
    Args:
        output_path: Path to save the plot. If None, displays the plot.
        std_threshold: Standard deviation threshold (default: 1.5)
        figsize: Figure size tuple (width, height) in inches (default: (14, 12))
    """
    # Fetch data for both types
    types = ['trailing', 'forward']
    type_labels = {
        'trailing': 'Q(-4)+Q(-3)+Q(-2)+Q(-1)',
        'forward': 'Q(0)+Q(1)+Q(2)+Q(3)'
    }
    type_colors = {
        'trailing': 'green',
        'forward': 'red'
    }
    
    data_dict = {}
    for pe_type in types:
        df = fetch_sp500_pe_ratio(type=pe_type)
        if not df.empty:
            df['Price_Date'] = pd.to_datetime(df['Price_Date'])
            df = df.sort_values('Price_Date')
            data_dict[pe_type] = df
    
    if not data_dict:
        raise ValueError("No P/E ratio data available. Please ensure EPS data is available.")
    
    # Create figure with 2 subplots
    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)
    today_str = datetime.now().strftime('%Y-%m-%d')
    fig.suptitle(
        f'S&P 500 Price with P/E Ratios (Last Updated: {today_str})',
        fontsize=16,
        fontweight='bold',
        y=0.995
    )
    
    for idx, pe_type in enumerate(types):
        if pe_type not in data_dict:
            continue
            
        ax = axes[idx]
        df = data_dict[pe_type]
        
        # Convert dates to numpy array for easier manipulation
        dates = pd.to_datetime(df['Price_Date']).values
        prices = df['Price'].values
        pe_ratios = df['PE_Ratio'].values
        
        # Use original data without any clipping or smoothing
        # Calculate statistics on original data
        pe_mean = np.mean(pe_ratios)
        pe_std = np.std(pe_ratios)
        upper_threshold = pe_mean + std_threshold * pe_std
        lower_threshold = pe_mean - std_threshold * pe_std
        
        # Create secondary y-axis for P/E ratio
        ax2 = ax.twinx()
        
        # Highlight periods outside ±1.5σ range - use vertical bands across full y-axis
        overvalued_mask = pe_ratios > upper_threshold
        undervalued_mask = pe_ratios < lower_threshold
        
        # Find continuous regions for vertical bands
        in_overvalued = False
        in_undervalued = False
        overvalued_start = None
        undervalued_start = None
        
        for i in range(len(dates)):
            if overvalued_mask[i]:
                if not in_overvalued:
                    overvalued_start = dates[i]
                    in_overvalued = True
            else:
                if in_overvalued:
                    ax.axvspan(overvalued_start, dates[i-1] if i > 0 else dates[0], 
                              alpha=0.2, color='red', zorder=0)
                    in_overvalued = False
            
            if undervalued_mask[i]:
                if not in_undervalued:
                    undervalued_start = dates[i]
                    in_undervalued = True
            else:
                if in_undervalued:
                    ax.axvspan(undervalued_start, dates[i-1] if i > 0 else dates[0], 
                              alpha=0.2, color='blue', zorder=0)
                    in_undervalued = False
        
        # Handle case where region extends to end
        if in_overvalued:
            ax.axvspan(overvalued_start, dates[-1], alpha=0.2, color='red', zorder=0)
        if in_undervalued:
            ax.axvspan(undervalued_start, dates[-1], alpha=0.2, color='blue', zorder=0)
        
        # Plot mean and threshold lines
        ax2.axhline(y=pe_mean, color='gray', linestyle='--', linewidth=1.2, alpha=0.7, zorder=1)
        ax2.axhline(y=upper_threshold, color='gold', linestyle=':', linewidth=1.2, alpha=0.7, zorder=1)
        ax2.axhline(y=lower_threshold, color='gold', linestyle=':', linewidth=1.2, alpha=0.7, zorder=1)
        
        # Plot S&P 500 Price (left axis) - smoother line
        ax.plot(dates, prices, 'k-', linewidth=1.8, label='S&P 500 Price', alpha=0.85, zorder=2)
        ax.set_ylabel('S&P 500 Price', fontsize=11, fontweight='bold')
        ax.tick_params(axis='y', labelsize=9)
        ax.grid(True, alpha=0.15, linestyle='-', linewidth=0.3)
        
        # Plot P/E Ratio (right axis) - use original values
        color = type_colors[pe_type]
        ax2.plot(dates, pe_ratios, color=color, linewidth=1.5, 
                label=f'{type_labels[pe_type]} P/E Ratio', alpha=0.7, zorder=3)
        ax2.set_ylabel('P/E Ratio', fontsize=11, fontweight='bold', color=color)
        ax2.tick_params(axis='y', labelsize=9, labelcolor=color)
        ax2.margins(y=0.2)  # Add 20% margin to y-axis
        
        # Set title
        ax.set_title(
            f'S&P 500 Price with {type_labels[pe_type]} P/E Ratio (Highlighting periods outside ±{std_threshold}σ range)',
            fontsize=12,
            fontweight='bold',
            pad=10
        )
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator((1, 7)))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=9)
        
        # Create cleaner legend
        legend_elements = [
            plt.Line2D([0], [0], color='black', linewidth=1.8, label='S&P 500 Price'),
            plt.Line2D([0], [0], color=color, linewidth=1.0, label=f'{type_labels[pe_type]} P/E Ratio', alpha=0.6),
            plt.Line2D([0], [0], color='gray', linestyle='--', linewidth=1.2, label=f'Mean: {pe_mean:.2f}'),
            plt.Line2D([0], [0], color='gold', linestyle=':', linewidth=1.2, label=f'+{std_threshold}σ: {upper_threshold:.2f}'),
            plt.Line2D([0], [0], color='gold', linestyle=':', linewidth=1.2, label=f'-{std_threshold}σ: {lower_threshold:.2f}'),
            plt.Rectangle((0, 0), 1, 1, facecolor='red', alpha=0.2, label=f'P/E > +{std_threshold}σ'),
            plt.Rectangle((0, 0), 1, 1, facecolor='blue', alpha=0.2, label=f'P/E < -{std_threshold}σ')
        ]
        
        ax.legend(handles=legend_elements, loc='upper left', fontsize=8, 
                 framealpha=0.9, edgecolor='lightgray')
    
    # Set x-axis label on bottom subplot
    axes[-1].set_xlabel('Date', fontsize=11, fontweight='bold')
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ Plot saved to {output_path}")
    else:
        plt.show()
    
    plt.close()

