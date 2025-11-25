"""P/E ratio calculation from EPS estimates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

# Type definitions
PE_RATIO_TYPE = Literal['forward', 'trailing']
import tempfile

import pandas as pd

from ..utils.csv_storage import read_csv


class SP500:
    """S&P 500 Market Data with EPS and P/E ratio calculations.
    
    Loads and caches S&P 500 price data and EPS estimates data.
    Provides convenient methods to calculate P/E ratios and EPS.
    
    Example:
        >>> from factset_report_analyzer.analysis import SP500
        >>> sp500 = SP500()
        >>> 
        >>> # Get current P/E ratio
        >>> current = sp500.current_pe
        >>> print(f"P/E: {current['pe_ratio']:.2f}")
        >>> 
        >>> # Get P/E ratio for specific date
        >>> pe = sp500.pe_ratio(pd.Timestamp('2024-01-01'))
        >>> 
        >>> # Get EPS for specific date
        >>> eps = sp500.eps(pd.Timestamp('2024-01-01'))
    """
    
    def __init__(self):
        """Initialize and load S&P 500 and EPS data."""
        self._df_eps = None
        self._price_df = None
        self._type: PE_RATIO_TYPE = 'forward'  # Default to forward
        self._load_data()
    
    def set_type(self, type: PE_RATIO_TYPE) -> None:
        """Set the type for EPS and P/E ratio calculations.
        
        Args:
            type: 'forward' or 'trailing'
            
        Example:
            >>> sp500 = SP500()
            >>> sp500.set_type('trailing')
            >>> eps = sp500.eps  # Now returns trailing EPS
        """
        if type not in ['forward', 'trailing']:
            raise ValueError("type must be 'forward' or 'trailing'")
        self._type = type
    
    def _load_data(self):
        """Load EPS and S&P 500 price data."""
        print("📊 Loading S&P 500 data...")
        
        # Load EPS data
        temp_path = Path(tempfile.gettempdir()) / "extracted_estimates.csv"
        self._df_eps = read_csv("extracted_estimates.csv", temp_path)
        
        if self._df_eps is None:
            raise FileNotFoundError(
                "EPS data not found. Please ensure extracted_estimates.csv is available."
            )
        
        self._df_eps['Report_Date'] = pd.to_datetime(self._df_eps['Report_Date'])
        self._df_eps = self._df_eps.sort_values('Report_Date')
        print(f"  ✅ EPS data: {len(self._df_eps)} reports")
        
        # Load S&P 500 price data
        min_date = self._df_eps['Report_Date'].min().strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            import yfinance as yf
            ticker = yf.Ticker('^GSPC')
            hist = ticker.history(start=min_date, end=end_date)
            self._price_df = pd.DataFrame({
                'Date': hist.index,
                'Price': hist['Close'].values
            })
            self._price_df['Date'] = pd.to_datetime(self._price_df['Date']).dt.tz_localize(None)  # Remove timezone
            self._price_df = self._price_df.sort_values('Date')
            print(f"  ✅ Price data: {len(self._price_df)} trading days")
        except ImportError:
            raise ImportError(
                "yfinance is required. Install with: pip install yfinance or uv add yfinance"
            )
        except Exception as e:
            raise Exception(f"Failed to load S&P 500 price data: {e}")
    
    @property
    def price(self) -> pd.DataFrame:
        """Get all S&P 500 price data.
        
        Returns:
            DataFrame with Date and Price columns
            
        Example:
            >>> sp500 = SP500()
            >>> prices = sp500.price
            >>> print(prices.head())
        """
        return self._price_df[['Date', 'Price']].copy()
    
    @property
    def eps(self) -> pd.DataFrame:
        """Get all EPS data based on current type setting.
        
        Returns:
            DataFrame with Date and EPS columns
            
        Example:
            >>> sp500 = SP500()
            >>> eps_data = sp500.eps  # forward (default)
            >>> sp500.set_type('trailing')
            >>> eps_data = sp500.eps  # trailing
        """
        dates = self._price_df['Date']
        eps_values = calculate_eps_sum(self._df_eps, dates, self._type)
        return pd.DataFrame({
            'Date': dates,
            'EPS': eps_values
        })
    
    @property
    def pe_ratio(self) -> pd.DataFrame:
        """Get all P/E ratio data based on current type setting.
        
        Returns:
            DataFrame with Date, Price, EPS, PE_Ratio, Type
            
        Example:
            >>> sp500 = SP500()
            >>> pe_df = sp500.pe_ratio  # forward (default)
            >>> sp500.set_type('trailing')
            >>> pe_df = sp500.pe_ratio  # trailing
        """
        dates = self._price_df['Date']
        price_data = self._price_df.copy()
        price_data['EPS'] = calculate_eps_sum(self._df_eps, dates, self._type)
        price_data['PE_Ratio'] = price_data['Price'] / price_data['EPS']
        price_data['Type'] = self._type
        return price_data[['Date', 'Price', 'EPS', 'PE_Ratio', 'Type']].reset_index(drop=True)
    
    @property
    def current_pe(self) -> dict:
        """Get current P/E ratio (most recent date with valid data).
        
        Returns:
            Dict with date, price, eps, pe_ratio, type
            
        Example:
            >>> sp500 = SP500()
            >>> current = sp500.current_pe
            >>> print(f"Forward P/E: {current['pe_ratio']:.2f}")
        """
        pe_df = self.pe_ratio
        # Find last row with valid EPS
        valid_df = pe_df.dropna(subset=['EPS'])
        if valid_df.empty:
            return None
        
        latest = valid_df.iloc[-1]
        return {
            'date': latest['Date'],
            'price': latest['Price'],
            'eps': latest['EPS'],
            'pe_ratio': latest['PE_Ratio'],
            'type': latest['Type']
        }
    
    @property
    def data(self) -> dict:
        """Get raw data DataFrames.
        
        Returns:
            Dict with 'eps' and 'price' DataFrames
        """
        return {
            'eps': self._df_eps,
            'price': self._price_df
        }
    

def quarter_mapper(report_date: pd.Timestamp, start: int, end: int = 0) -> list[str]:
    """Map relative quarter positions to quarter column names.
    
    Args:
        report_date: Timestamp of the report date
        start: Relative start position (e.g., -4 for 4 quarters before current)
        end: Relative end position (e.g., 0 for current quarter, inclusive)
        
    Returns:
        List of quarter column names (e.g., ["Q1'19", "Q2'19", "Q3'19", "Q4'19"])
    """
    base_quarter = report_date.quarter
    base_year = report_date.year
    
    # Generate quarter range
    quarters = []
    for i in range(start, end + 1):
        # Calculate quarter and year with offset
        total_quarters = (base_year * 4 + base_quarter - 1) + i
        q = (total_quarters % 4) + 1
        y = (total_quarters // 4) % 100
        quarters.append(f"Q{q}'{y:02d}")
    
    return quarters


def calculate_eps_sum(
    df_eps: pd.DataFrame,
    dates: pd.Series,
    type: PE_RATIO_TYPE
) -> pd.Series:
    """Calculate 4-quarter EPS sum for given dates.
    
    Args:
        df_eps: DataFrame with EPS data (must have 'Report_Date' column)
        dates: Series of dates to calculate EPS for
        type: Type of EPS calculation ('forward' or 'trailing')
        
    Returns:
        Series of EPS sums
        
    Example:
        >>> eps_series = calculate_eps_sum(df_eps, df['Report_Date'], 'forward')
    """
    df_eps_sorted = df_eps.sort_values('Report_Date')
    
    results = [
        _calculate_eps_for_date(df_eps_sorted, date, type)
        for date in dates
    ]
    return pd.Series(results, index=dates.index)


def _calculate_eps_for_date(
    df_eps_sorted: pd.DataFrame,
    price_date: pd.Timestamp,
    type: PE_RATIO_TYPE
) -> float | None:
    """Calculate 4-quarter EPS sum for a single date."""
    # Get quarter column names using price_date
    if type == 'forward':
        needed_quarters = quarter_mapper(price_date, 0, 3)
    else:  # trailing
        needed_quarters = quarter_mapper(price_date, -4, -1)
    
    # Filter to only needed quarter columns
    eps_candidates = df_eps_sorted[df_eps_sorted['Report_Date'] <= price_date]
    if eps_candidates.empty:
        return None
    
    eps_filtered = eps_candidates[needed_quarters]
    
    # Get most recent value for each quarter column
    values = [
        float(str(eps_filtered[col].dropna().iloc[-1]).replace('*', '').strip())
        for col in needed_quarters
        if col in eps_filtered.columns and not eps_filtered[col].dropna().empty
    ]
    
    if len(values) == 4:
        return sum(values) if sum(values) > 0 else None
    
    return None


if __name__ == "__main__":
    # Example usage
    sp500 = SP500()
    print("Current P/E Ratio:")
    current = sp500.current_pe
    print(f"  Date: {current['date']}")
    print(f"  P/E: {current['pe_ratio']:.2f}")
