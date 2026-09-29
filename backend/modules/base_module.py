"""
Base Module Interface for DoughFlow Financial Modules

All financial modules (income sources, accounts, investments, debts, expenses)
must implement this interface to participate in the flow graph simulation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from decimal import Decimal


class ModuleType(Enum):
    """Categories of financial modules"""
    INCOME_SOURCE = "income_source"      # Salary, business income
    ACCOUNT = "account"                   # Checking, savings
    INVESTMENT = "investment"             # Stocks, 401k, 529, IRA, real estate
    DEBT = "debt"                         # Mortgage, student loan, credit card
    EXPENSE = "expense"                   # Fixed, variable, tax


class FlowDirection(Enum):
    """Direction of money flow for a module"""
    INFLOW = "inflow"      # Money comes in (income sources)
    OUTFLOW = "outflow"    # Money goes out (expenses)
    BOTH = "both"          # Both directions (accounts, investments)


@dataclass
class TaxInfo:
    """Tax-related information for a transaction or module state"""
    taxable_income: float = 0.0
    tax_deferred_income: float = 0.0      # e.g., 401k contributions
    tax_exempt_income: float = 0.0        # e.g., Roth distributions
    capital_gains_short: float = 0.0      # Short-term capital gains
    capital_gains_long: float = 0.0       # Long-term capital gains
    qualified_dividends: float = 0.0
    ordinary_dividends: float = 0.0
    deductions: Dict[str, float] = field(default_factory=dict)  # e.g., mortgage interest
    credits: Dict[str, float] = field(default_factory=dict)     # e.g., child tax credit
    withholding: float = 0.0              # Tax already withheld


@dataclass
class ModuleState:
    """Current state of a module at a point in time"""
    balance: float = 0.0                  # Current value/balance
    monthly_contribution: float = 0.0     # Regular monthly inflow
    monthly_withdrawal: float = 0.0       # Regular monthly outflow
    cost_basis: float = 0.0               # For investments: original cost
    tax_info: TaxInfo = field(default_factory=TaxInfo)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True                # Whether this module is currently active


@dataclass
class FlowResult:
    """Result of processing a flow for one month"""
    amount_received: float = 0.0          # Amount received from inflows
    amount_sent: float = 0.0              # Amount sent to outflows
    new_state: ModuleState = field(default_factory=ModuleState)
    tax_info: TaxInfo = field(default_factory=TaxInfo)
    events: List[str] = field(default_factory=list)  # Notable events (e.g., "401k limit reached")


class BaseModule(ABC):
    """
    Abstract base class for all financial modules.

    Each module represents a node in the financial flow graph.
    """

    def __init__(self, node_id: str, config: Dict[str, Any]):
        """
        Initialize the module.

        Args:
            node_id: Unique identifier for this node in the graph
            config: Module-specific configuration parameters
        """
        self.node_id = node_id
        self.config = config
        self._state = ModuleState()
        self._validate_config()

    @property
    @abstractmethod
    def module_type(self) -> ModuleType:
        """Return the type of this module"""
        pass

    @property
    @abstractmethod
    def flow_direction(self) -> FlowDirection:
        """Return the flow direction for this module"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for display"""
        pass

    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Return JSON schema for module configuration.
        Used for form generation in the frontend.
        """
        pass

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate module configuration, raise ValueError if invalid"""
        pass

    @abstractmethod
    def initialize(self, start_date: str) -> ModuleState:
        """
        Initialize module state at simulation start.

        Args:
            start_date: Simulation start date (YYYY-MM format)

        Returns:
            Initial module state
        """
        pass

    @abstractmethod
    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        """
        Process one month of simulation.

        Args:
            month: Month number (1-12)
            year: Year (e.g., 2024)
            inflows: Dict of source_node_id -> amount received
            available_for_outflow: Total amount available to send to connected nodes
            user_profile: User's tax/demographic info

        Returns:
            FlowResult with new state and amounts transferred
        """
        pass

    @abstractmethod
    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        """
        Get annual summary for tax reporting.

        Args:
            year: The year to summarize

        Returns:
            Dict with annual totals relevant to this module type
        """
        pass

    def get_state(self) -> ModuleState:
        """Get current module state"""
        return self._state

    def set_state(self, state: ModuleState) -> None:
        """Set module state (used for loading saved simulations)"""
        self._state = state

    def is_active_for_date(self, year: int, month: int) -> bool:
        """
        Check if this module is active for the given year/month.
        Uses start_year, start_month, end_year, end_month from config.
        """
        start_year = self.config.get('start_year', 0)
        start_month = self.config.get('start_month', 1)
        end_year = self.config.get('end_year', 0)
        end_month = self.config.get('end_month', 0)

        # Convert to comparable format (YYYYMM)
        current = year * 100 + month

        # Check start date
        if start_year > 0:
            start = start_year * 100 + start_month
            if current < start:
                return False

        # Check end date (0 = no end date)
        if end_year > 0 and end_month > 0:
            end = end_year * 100 + end_month
            if current > end:
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize module to dictionary for saving"""
        return {
            'node_id': self.node_id,
            'module_type': self.module_type.value,
            'config': self.config,
            'state': {
                'balance': self._state.balance,
                'monthly_contribution': self._state.monthly_contribution,
                'monthly_withdrawal': self._state.monthly_withdrawal,
                'cost_basis': self._state.cost_basis,
                'metadata': self._state.metadata,
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModule':
        """Deserialize module from dictionary"""
        instance = cls(data['node_id'], data['config'])
        if 'state' in data:
            instance._state = ModuleState(
                balance=data['state'].get('balance', 0.0),
                monthly_contribution=data['state'].get('monthly_contribution', 0.0),
                monthly_withdrawal=data['state'].get('monthly_withdrawal', 0.0),
                cost_basis=data['state'].get('cost_basis', 0.0),
                metadata=data['state'].get('metadata', {}),
            )
        return instance


# Registry of all module types for factory pattern
MODULE_REGISTRY: Dict[str, type] = {}


def register_module(cls: type) -> type:
    """Decorator to register a module class"""
    MODULE_REGISTRY[cls.__name__] = cls
    return cls


def create_module(module_type: str, node_id: str, config: Dict[str, Any]) -> BaseModule:
    """Factory function to create module instances"""
    if module_type not in MODULE_REGISTRY:
        raise ValueError(f"Unknown module type: {module_type}")
    return MODULE_REGISTRY[module_type](node_id, config)
