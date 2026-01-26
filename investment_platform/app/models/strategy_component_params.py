"""
Strategy Component Parameters Model

Stores component-level trading parameter overrides.
Parameters can be set at sector, subsector, or symbol level with inheritance.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime

from app.database import Base, get_scoped_session, is_csv_backend, get_csv_storage


class StrategyComponentParams(Base):
    """
    Represents trading parameter overrides for a strategy component.

    Parameters are inherited: Symbol → Subsector → Sector → Strategy defaults.
    Only non-null values override the parent level.

    Attributes:
        id: Primary key
        strategy_id: The strategy these params belong to
        component_path: Path of the component (sector, subsector, or symbol)
        max_position_pct: Maximum position size as % of portfolio
        stop_loss_percent: Stop loss trigger percentage
        take_profit_percent: Take profit trigger percentage
        trade_frequency_multiplier: Multiplier for base trade frequency
        entry_signal: Entry signal type (e.g., 'sma_crossover', 'momentum')
        exit_signal: Exit signal type
        created_at: Record creation timestamp
    """
    __tablename__ = 'strategy_component_params'

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(50), nullable=False, index=True)
    component_path = Column(String(100), nullable=False)

    # Trading Parameters (nullable = use inherited value)
    max_position_pct = Column(Float)
    stop_loss_percent = Column(Integer)
    take_profit_percent = Column(Integer)
    trade_frequency_multiplier = Column(Float)
    entry_signal = Column(String(50))
    exit_signal = Column(String(50))

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Valid signal types
    SIGNAL_TYPES = [
        'sma_crossover',
        'ema_crossover',
        'momentum',
        'rsi_oversold',
        'rsi_overbought',
        'macd_signal',
        'bollinger_breakout',
        'volume_spike',
        'price_breakout',
        'mean_reversion'
    ]

    def __repr__(self):
        return f'<StrategyComponentParams {self.strategy_id}/{self.component_path}>'

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'strategy_id': self.strategy_id,
            'component_path': self.component_path,
            'max_position_pct': self.max_position_pct,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'trade_frequency_multiplier': self.trade_frequency_multiplier,
            'entry_signal': self.entry_signal,
            'exit_signal': self.exit_signal,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def validate(self):
        """Validate component params."""
        errors = []

        if not self.strategy_id:
            errors.append("strategy_id is required")

        if not self.component_path:
            errors.append("component_path is required")

        if self.max_position_pct is not None and not 0.01 <= self.max_position_pct <= 1.0:
            errors.append("max_position_pct must be between 0.01 and 1.0")

        if self.stop_loss_percent is not None and not 1 <= self.stop_loss_percent <= 50:
            errors.append("stop_loss_percent must be between 1 and 50")

        if self.take_profit_percent is not None and not 1 <= self.take_profit_percent <= 200:
            errors.append("take_profit_percent must be between 1 and 200")

        if self.trade_frequency_multiplier is not None and not 0.1 <= self.trade_frequency_multiplier <= 10.0:
            errors.append("trade_frequency_multiplier must be between 0.1 and 10.0")

        if self.entry_signal is not None and self.entry_signal not in self.SIGNAL_TYPES:
            errors.append(f"entry_signal must be one of: {', '.join(self.SIGNAL_TYPES)}")

        if self.exit_signal is not None and self.exit_signal not in self.SIGNAL_TYPES:
            errors.append(f"exit_signal must be one of: {', '.join(self.SIGNAL_TYPES)}")

        if errors:
            raise ValueError('; '.join(errors))

    @classmethod
    def get_params(cls, strategy_id, component_path):
        """Get params for a specific component."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_component_params(strategy_id, component_path)

        session = get_scoped_session()
        return session.query(cls).filter_by(
            strategy_id=strategy_id,
            component_path=component_path
        ).first()

    @classmethod
    def get_all_params(cls, strategy_id):
        """Get all component params for a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_all_strategy_component_params(strategy_id)

        session = get_scoped_session()
        return session.query(cls).filter_by(strategy_id=strategy_id).all()

    @classmethod
    def set_params(cls, strategy_id, component_path, **params):
        """Set or update params for a component."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.set_strategy_component_params(strategy_id, component_path, **params)

        session = get_scoped_session()
        existing = cls.get_params(strategy_id, component_path)

        if existing:
            for key, value in params.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.validate()
            session.commit()
            return existing
        else:
            new_params = cls(
                strategy_id=strategy_id,
                component_path=component_path,
                **params
            )
            new_params.validate()
            session.add(new_params)
            session.commit()
            return new_params

    @classmethod
    def delete_params(cls, strategy_id, component_path):
        """Delete params for a component."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.delete_strategy_component_params(strategy_id, component_path)

        session = get_scoped_session()
        params = cls.get_params(strategy_id, component_path)
        if params:
            session.delete(params)
            session.commit()
            return True
        return False

    @classmethod
    def delete_all_for_strategy(cls, strategy_id):
        """Delete all component params for a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.delete_all_strategy_component_params(strategy_id)

        session = get_scoped_session()
        params = cls.get_all_params(strategy_id)
        for param in params:
            session.delete(param)
        session.commit()
        return True
