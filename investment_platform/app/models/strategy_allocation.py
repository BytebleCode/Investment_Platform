"""
Strategy Allocation Model

Stores hierarchical allocations for strategies (sector, subsector, or symbol level).
Supports weighted allocation at any level of the hierarchy.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime

from app.database import Base, get_scoped_session, is_csv_backend, get_csv_storage


class StrategyAllocation(Base):
    """
    Represents a weighted allocation within a strategy.

    Allocations can be at sector, subsector, or individual symbol level.
    The path uses dot notation: 'financials', 'financials.banks', or 'JPM'.

    Attributes:
        id: Primary key
        strategy_id: The strategy this allocation belongs to
        allocation_type: 'sector', 'subsector', or 'symbol'
        path: Hierarchical path (e.g., 'financials.banks' or 'JPM')
        weight: Allocation weight (0.0 to 1.0)
        parent_path: Parent allocation path (for inheritance)
        is_active: Whether this allocation is currently active
        created_at: Record creation timestamp
        updated_at: Last modification timestamp
    """
    __tablename__ = 'strategy_allocations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(50), nullable=False, index=True)
    allocation_type = Column(String(20), nullable=False)  # sector, subsector, symbol
    path = Column(String(100), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    parent_path = Column(String(100))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Composite unique constraint on strategy_id and path
    __table_args__ = (
        # Unique constraint handled by path uniqueness per strategy
    )

    def __repr__(self):
        return f'<StrategyAllocation {self.strategy_id}/{self.path} ({self.weight})>'

    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'strategy_id': self.strategy_id,
            'allocation_type': self.allocation_type,
            'path': self.path,
            'weight': self.weight,
            'parent_path': self.parent_path,
            'is_active': bool(self.is_active),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def validate(self):
        """Validate allocation parameters."""
        errors = []

        if not self.strategy_id:
            errors.append("strategy_id is required")

        if self.allocation_type not in ('sector', 'subsector', 'symbol'):
            errors.append("allocation_type must be 'sector', 'subsector', or 'symbol'")

        if not self.path:
            errors.append("path is required")

        if not 0.0 <= self.weight <= 1.0:
            errors.append("weight must be between 0.0 and 1.0")

        if errors:
            raise ValueError('; '.join(errors))

    @classmethod
    def get_allocations(cls, strategy_id, include_inactive=False):
        """Get all allocations for a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_allocations(strategy_id, include_inactive)

        session = get_scoped_session()
        query = session.query(cls).filter_by(strategy_id=strategy_id)
        if not include_inactive:
            query = query.filter_by(is_active=1)
        return query.order_by(cls.path).all()

    @classmethod
    def get_allocation(cls, allocation_id):
        """Get a specific allocation by ID."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_allocation(allocation_id)

        session = get_scoped_session()
        return session.query(cls).filter_by(id=allocation_id).first()

    @classmethod
    def get_by_path(cls, strategy_id, path):
        """Get allocation by strategy and path."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_strategy_allocation_by_path(strategy_id, path)

        session = get_scoped_session()
        return session.query(cls).filter_by(strategy_id=strategy_id, path=path).first()

    @classmethod
    def create(cls, strategy_id, allocation_type, path, weight=1.0, parent_path=None):
        """Create a new allocation."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.create_strategy_allocation(
                strategy_id=strategy_id,
                allocation_type=allocation_type,
                path=path,
                weight=weight,
                parent_path=parent_path
            )

        session = get_scoped_session()
        allocation = cls(
            strategy_id=strategy_id,
            allocation_type=allocation_type,
            path=path,
            weight=weight,
            parent_path=parent_path
        )
        allocation.validate()
        session.add(allocation)
        session.commit()
        return allocation

    @classmethod
    def update(cls, allocation_id, **kwargs):
        """Update an existing allocation."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.update_strategy_allocation(allocation_id, **kwargs)

        session = get_scoped_session()
        allocation = cls.get_allocation(allocation_id)
        if not allocation:
            return None

        for key, value in kwargs.items():
            if hasattr(allocation, key):
                setattr(allocation, key, value)
        allocation.updated_at = datetime.now(timezone.utc)
        allocation.validate()
        session.commit()
        return allocation

    @classmethod
    def delete(cls, allocation_id, hard_delete=False):
        """Delete (or deactivate) an allocation."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.delete_strategy_allocation(allocation_id, hard_delete)

        session = get_scoped_session()
        allocation = cls.get_allocation(allocation_id)
        if not allocation:
            return False

        if hard_delete:
            session.delete(allocation)
        else:
            allocation.is_active = 0
            allocation.updated_at = datetime.now(timezone.utc)
        session.commit()
        return True

    @classmethod
    def delete_all_for_strategy(cls, strategy_id, hard_delete=False):
        """Delete all allocations for a strategy."""
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.delete_all_strategy_allocations(strategy_id, hard_delete)

        session = get_scoped_session()
        allocations = cls.get_allocations(strategy_id, include_inactive=True)
        for alloc in allocations:
            if hard_delete:
                session.delete(alloc)
            else:
                alloc.is_active = 0
                alloc.updated_at = datetime.now(timezone.utc)
        session.commit()
        return True
