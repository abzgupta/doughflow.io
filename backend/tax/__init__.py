"""
DoughFlow Tax Engine
Handles federal and state tax calculations, deductions, and credits.
"""

from .federal_tax import FederalTaxCalculator, FilingStatus
from .deductions import DeductionCalculator
from .state_tax import StateTaxCalculator, StateTaxType

__all__ = [
    'FederalTaxCalculator',
    'FilingStatus',
    'DeductionCalculator',
    'StateTaxCalculator',
    'StateTaxType',
]
