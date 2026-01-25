"""
Macro Signals Service

Fetches and normalizes macroeconomic signals from the FRED API
(Federal Reserve Economic Data) for strategy regime detection.
"""
import os
import logging
from datetime import datetime, timedelta
from functools import lru_cache

import requests

logger = logging.getLogger(__name__)


# FRED API Configuration
FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
FRED_BASE_URL = 'https://api.stlouisfed.org/fred/series/observations'

# Cache for signal values (TTL managed by caching mechanism)
_signal_cache = {}
_cache_expiry = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache


# Signal normalization ranges (historical context)
# Format: (series_id, min_typical, max_typical, invert)
SIGNAL_RANGES = {
    # Interest Rates
    'FEDFUNDS': (0, 6, False),       # Fed Funds: 0-6% range
    'T10Y2Y': (-1, 3, False),         # 2Y-10Y spread: -1 to 3%
    'DFII10': (-2, 3, False),         # 10Y real rate: -2 to 3%

    # Inflation
    'CPIAUCSL': (0, 10, False),       # CPI YoY: 0-10%
    'PCEPILFE': (0, 6, False),        # Core PCE: 0-6%
    'T10YIE': (0, 4, False),          # 10Y breakeven: 0-4%
    'PPIACO': (-5, 15, False),        # PPI YoY: -5 to 15%

    # Growth & Activity
    'ISM/MAN_PMI': (40, 65, False),   # ISM PMI: 40-65
    'INDPRO': (-10, 10, False),       # Industrial prod YoY: -10 to 10%
    'RSAFS': (-15, 20, False),        # Retail sales YoY: -15 to 20%
    'USSLIND': (-5, 5, False),        # LEI: -5 to 5%

    # Credit & Financial Conditions
    'BAMLH0A0HYM2': (2, 10, True),    # HY spread: 2-10% (inverted: high = bad)
    'NFCI': (-1, 1, True),            # NFCI: -1 to 1 (inverted: positive = tight)
    'M2SL': (-5, 25, False),          # M2 YoY: -5 to 25%
    'DRTSCILM': (-30, 80, True),      # Loan officer survey (inverted)

    # Labor
    'ICSA': (150, 500, True),         # Initial claims 000s (inverted: high = bad)
    'UNRATE': (3, 10, True),          # Unemployment rate (inverted)
}


# Regime thresholds
REGIME_THRESHOLDS = {
    'risk_on': (0.6, 1.0),
    'growth': (0.2, 0.6),
    'neutral': (-0.2, 0.2),
    'slowdown': (-0.6, -0.2),
    'recession': (-1.0, -0.6)
}


class MacroSignalService:
    """
    Fetches and processes macroeconomic signals from FRED API.
    """

    def __init__(self, api_key=None):
        """
        Initialize the macro signal service.

        Args:
            api_key: FRED API key (uses env var FRED_API_KEY if not provided)
        """
        self.api_key = api_key or FRED_API_KEY
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.warning("FRED API key not configured. Macro signals disabled.")

    def is_enabled(self):
        """Check if FRED API is configured and available."""
        return self.enabled

    def get_signal(self, series_id, transform=None, lookback_days=365):
        """
        Fetch the latest value for a FRED series.

        Args:
            series_id: FRED series identifier (e.g., 'FEDFUNDS')
            transform: Optional transformation ('yoy' for year-over-year change)
            lookback_days: Days of history to fetch for transforms

        Returns:
            float: Latest signal value, or None if unavailable
        """
        if not self.enabled:
            return None

        # Check cache
        cache_key = f"{series_id}:{transform}"
        if cache_key in _signal_cache:
            expiry = _cache_expiry.get(cache_key, datetime.min)
            if datetime.now() < expiry:
                return _signal_cache[cache_key]

        try:
            # Handle ISM PMI special case (different source)
            if series_id.startswith('ISM/'):
                # ISM data requires separate handling
                # For now, return simulated neutral value
                return 52.0

            # Fetch from FRED
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)

            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date.strftime('%Y-%m-%d'),
                'observation_end': end_date.strftime('%Y-%m-%d'),
                'sort_order': 'desc',
                'limit': 15 if transform == 'yoy' else 1
            }

            response = requests.get(FRED_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            observations = data.get('observations', [])
            if not observations:
                logger.warning(f"No data for FRED series: {series_id}")
                return None

            # Get latest value
            latest = observations[0]
            if latest['value'] == '.':
                return None

            value = float(latest['value'])

            # Apply year-over-year transform if needed
            if transform == 'yoy' and len(observations) >= 13:
                # Find observation from ~1 year ago
                year_ago = None
                for obs in observations:
                    if obs['value'] != '.':
                        obs_date = datetime.strptime(obs['date'], '%Y-%m-%d')
                        if (end_date - obs_date).days >= 360:
                            year_ago = float(obs['value'])
                            break

                if year_ago and year_ago != 0:
                    value = ((value - year_ago) / abs(year_ago)) * 100

            # Cache result
            _signal_cache[cache_key] = value
            _cache_expiry[cache_key] = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)

            return value

        except requests.RequestException as e:
            logger.error(f"FRED API error for {series_id}: {e}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Error parsing FRED data for {series_id}: {e}")
            return None

    def normalize_signal(self, value, series_id):
        """
        Normalize a signal value to -1 to +1 range.

        Args:
            value: Raw signal value
            series_id: FRED series identifier

        Returns:
            float: Normalized value between -1 and +1
        """
        if value is None:
            return 0.0

        # Get normalization parameters
        if series_id not in SIGNAL_RANGES:
            return 0.0

        min_val, max_val, invert = SIGNAL_RANGES[series_id]

        # Clip to range
        clipped = max(min_val, min(max_val, value))

        # Normalize to 0-1
        normalized = (clipped - min_val) / (max_val - min_val) if max_val != min_val else 0.5

        # Convert to -1 to +1
        result = (normalized * 2) - 1

        # Invert if needed (for signals where higher = worse)
        if invert:
            result = -result

        return result

    def calculate_regime_score(self, strategy_signals):
        """
        Calculate aggregate macro regime score for a strategy.

        Args:
            strategy_signals: Dict of signal configs from strategy definition
                e.g., {
                    'fed_funds_rate': {'series': 'FEDFUNDS', 'weight': 0.30},
                    'yield_curve': {'series': 'T10Y2Y', 'weight': 0.35, 'invert': True}
                }

        Returns:
            float: Aggregate score between -1.0 and +1.0
        """
        if not self.enabled:
            return 0.0  # Neutral when disabled

        total_weight = 0
        weighted_sum = 0

        for signal_name, config in strategy_signals.items():
            series_id = config.get('series')
            weight = config.get('weight', 1.0)
            transform = config.get('transform')
            invert = config.get('invert', False)

            if not series_id:
                continue

            # Fetch signal
            value = self.get_signal(series_id, transform)
            if value is None:
                continue

            # Normalize
            normalized = self.normalize_signal(value, series_id)

            # Apply signal-level inversion
            if invert:
                normalized = -normalized

            weighted_sum += normalized * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def get_regime(self, score):
        """
        Map a regime score to a regime label.

        Args:
            score: Aggregate regime score (-1.0 to +1.0)

        Returns:
            str: Regime label
        """
        for regime, (min_score, max_score) in REGIME_THRESHOLDS.items():
            if min_score <= score < max_score:
                return regime
        return 'neutral'

    def get_regime_for_strategy(self, strategy):
        """
        Get the current macro regime for a strategy.

        Args:
            strategy: Strategy dict with 'signals' configuration

        Returns:
            dict: Regime info with score, label, and signal details
        """
        signals = strategy.get('signals', {})

        if not signals or not self.enabled:
            return {
                'score': 0.0,
                'regime': 'neutral',
                'enabled': self.enabled,
                'signals': {}
            }

        score = self.calculate_regime_score(signals)
        regime = self.get_regime(score)

        # Get individual signal values
        signal_details = {}
        for signal_name, config in signals.items():
            series_id = config.get('series')
            transform = config.get('transform')

            value = self.get_signal(series_id, transform)
            normalized = self.normalize_signal(value, series_id) if value is not None else None

            signal_details[signal_name] = {
                'series': series_id,
                'raw_value': value,
                'normalized': normalized,
                'weight': config.get('weight', 1.0)
            }

        return {
            'score': round(score, 3),
            'regime': regime,
            'enabled': True,
            'signals': signal_details
        }


# Global service instance
_service_instance = None


def get_macro_service():
    """Get or create the global MacroSignalService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = MacroSignalService()
    return _service_instance


def get_regime_for_strategy(strategy):
    """Convenience function to get regime for a strategy."""
    service = get_macro_service()
    return service.get_regime_for_strategy(strategy)


def clear_signal_cache():
    """Clear the signal cache (useful for testing)."""
    global _signal_cache, _cache_expiry
    _signal_cache = {}
    _cache_expiry = {}
