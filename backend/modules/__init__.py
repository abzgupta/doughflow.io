"""
DoughFlow Financial Modules
Each module represents a type of financial entity in the flow graph.
"""

from .base_module import BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo

# Import all module types
try:
    from .real_estate import RealEstateModule
except ImportError:
    RealEstateModule = None

try:
    from .salary import SalaryModule
except ImportError:
    SalaryModule = None

try:
    from .savings_account import SavingsAccountModule
except ImportError:
    SavingsAccountModule = None

try:
    from .stock_portfolio import StockPortfolioModule
except ImportError:
    StockPortfolioModule = None

try:
    from .four_oh_one_k import FourOhOneKModule
except ImportError:
    FourOhOneKModule = None

try:
    from .five_twenty_nine import FiveTwentyNineModule
except ImportError:
    FiveTwentyNineModule = None

try:
    from .ira import IRAModule
except ImportError:
    IRAModule = None

try:
    from .mortgage import MortgageModule
except ImportError:
    MortgageModule = None

try:
    from .debt import DebtModule
except ImportError:
    DebtModule = None

try:
    from .expense import ExpenseModule
except ImportError:
    ExpenseModule = None

__all__ = [
    'BaseModule',
    'ModuleType',
    'FlowDirection',
    'ModuleState',
    'FlowResult',
    'TaxInfo',
    'RealEstateModule',
    'SalaryModule',
    'SavingsAccountModule',
    'StockPortfolioModule',
    'FourOhOneKModule',
    'FiveTwentyNineModule',
    'IRAModule',
    'MortgageModule',
    'DebtModule',
    'ExpenseModule',
]
