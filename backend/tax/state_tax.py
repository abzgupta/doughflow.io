"""
State Tax Calculator

Handles state income tax calculations for all 50 states.
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class StateTaxType(Enum):
    NONE = "none"           # No state income tax
    FLAT = "flat"           # Flat rate
    PROGRESSIVE = "progressive"  # Progressive brackets


@dataclass
class StateTaxInfo:
    """State tax configuration"""
    state: str
    tax_type: StateTaxType
    flat_rate: float = 0.0
    brackets: List[tuple] = None  # [(min, max, rate), ...]
    standard_deduction_single: float = 0.0
    standard_deduction_mfj: float = 0.0
    personal_exemption: float = 0.0
    notes: str = ""


@dataclass
class StateTaxResult:
    """Result of state tax calculation"""
    state: str
    taxable_income: float = 0.0
    tax_liability: float = 0.0
    effective_rate: float = 0.0
    marginal_rate: float = 0.0
    deductions_used: float = 0.0


class StateTaxCalculator:
    """
    Calculate state income tax for various states.

    Supports:
    - No income tax states (TX, FL, WA, etc.)
    - Flat tax states (IL, PA, etc.)
    - Progressive tax states (CA, NY, etc.)
    """

    # 2024 State Tax Configurations
    STATE_CONFIGS = {
        # No Income Tax States
        'AK': StateTaxInfo('Alaska', StateTaxType.NONE),
        'FL': StateTaxInfo('Florida', StateTaxType.NONE),
        'NV': StateTaxInfo('Nevada', StateTaxType.NONE),
        'SD': StateTaxInfo('South Dakota', StateTaxType.NONE),
        'TX': StateTaxInfo('Texas', StateTaxType.NONE),
        'WA': StateTaxInfo('Washington', StateTaxType.NONE),
        'WY': StateTaxInfo('Wyoming', StateTaxType.NONE),
        'NH': StateTaxInfo('New Hampshire', StateTaxType.NONE, notes="Interest/dividends only"),
        'TN': StateTaxInfo('Tennessee', StateTaxType.NONE),

        # Flat Tax States
        'CO': StateTaxInfo('Colorado', StateTaxType.FLAT, flat_rate=0.044),
        'IL': StateTaxInfo('Illinois', StateTaxType.FLAT, flat_rate=0.0495),
        'IN': StateTaxInfo('Indiana', StateTaxType.FLAT, flat_rate=0.0305),
        'KY': StateTaxInfo('Kentucky', StateTaxType.FLAT, flat_rate=0.04),
        'MA': StateTaxInfo('Massachusetts', StateTaxType.FLAT, flat_rate=0.05,
                          notes="Additional 4% on income over $1M"),
        'MI': StateTaxInfo('Michigan', StateTaxType.FLAT, flat_rate=0.0425),
        'NC': StateTaxInfo('North Carolina', StateTaxType.FLAT, flat_rate=0.0475),
        'PA': StateTaxInfo('Pennsylvania', StateTaxType.FLAT, flat_rate=0.0307),
        'UT': StateTaxInfo('Utah', StateTaxType.FLAT, flat_rate=0.0465),

        # Progressive Tax States (2024 brackets for Single filers)
        'CA': StateTaxInfo('California', StateTaxType.PROGRESSIVE,
            brackets=[
                (0, 10412, 0.01),
                (10412, 24684, 0.02),
                (24684, 38959, 0.04),
                (38959, 54081, 0.06),
                (54081, 68350, 0.08),
                (68350, 349137, 0.093),
                (349137, 418961, 0.103),
                (418961, 698271, 0.113),
                (698271, float('inf'), 0.123),
            ],
            standard_deduction_single=5363,
            standard_deduction_mfj=10726),

        'NY': StateTaxInfo('New York', StateTaxType.PROGRESSIVE,
            brackets=[
                (0, 8500, 0.04),
                (8500, 11700, 0.045),
                (11700, 13900, 0.0525),
                (13900, 80650, 0.0550),
                (80650, 215400, 0.06),
                (215400, 1077550, 0.0685),
                (1077550, 5000000, 0.0965),
                (5000000, 25000000, 0.103),
                (25000000, float('inf'), 0.109),
            ],
            standard_deduction_single=8000,
            standard_deduction_mfj=16050),

        'NJ': StateTaxInfo('New Jersey', StateTaxType.PROGRESSIVE,
            brackets=[
                (0, 20000, 0.014),
                (20000, 35000, 0.0175),
                (35000, 40000, 0.035),
                (40000, 75000, 0.05525),
                (75000, 500000, 0.0637),
                (500000, 1000000, 0.0897),
                (1000000, float('inf'), 0.1075),
            ]),

        'GA': StateTaxInfo('Georgia', StateTaxType.PROGRESSIVE,
            brackets=[
                (0, 750, 0.01),
                (750, 2250, 0.02),
                (2250, 3750, 0.03),
                (3750, 5250, 0.04),
                (5250, 7000, 0.05),
                (7000, float('inf'), 0.055),
            ],
            standard_deduction_single=5400,
            standard_deduction_mfj=7100),

        'OH': StateTaxInfo('Ohio', StateTaxType.PROGRESSIVE,
            brackets=[
                (0, 26050, 0.0),
                (26050, 100000, 0.02765),
                (100000, float('inf'), 0.0375),
            ]),

        'VA': StateTaxInfo('Virginia', StateTaxType.PROGRESSIVE,
            brackets=[
                (0, 3000, 0.02),
                (3000, 5000, 0.03),
                (5000, 17000, 0.05),
                (17000, float('inf'), 0.0575),
            ],
            standard_deduction_single=8000,
            standard_deduction_mfj=16000),

        'MN': StateTaxInfo('Minnesota', StateTaxType.PROGRESSIVE,
            brackets=[
                (0, 31690, 0.0535),
                (31690, 104090, 0.068),
                (104090, 183340, 0.0785),
                (183340, float('inf'), 0.0985),
            ],
            standard_deduction_single=14575,
            standard_deduction_mfj=29150),

        'OR': StateTaxInfo('Oregon', StateTaxType.PROGRESSIVE,
            brackets=[
                (0, 4050, 0.0475),
                (4050, 10200, 0.0675),
                (10200, 125000, 0.0875),
                (125000, float('inf'), 0.099),
            ],
            standard_deduction_single=2605,
            standard_deduction_mfj=5210),

        'AZ': StateTaxInfo('Arizona', StateTaxType.FLAT, flat_rate=0.025),

        'WI': StateTaxInfo('Wisconsin', StateTaxType.PROGRESSIVE,
            brackets=[
                (0, 14320, 0.0354),
                (14320, 28640, 0.0465),
                (28640, 315310, 0.053),
                (315310, float('inf'), 0.0765),
            ],
            standard_deduction_single=13230,
            standard_deduction_mfj=24480),
    }

    def __init__(self, state: str, filing_status: str = 'single'):
        self.state = state.upper()
        self.filing_status = filing_status
        self.config = self.STATE_CONFIGS.get(self.state)

    def calculate(
        self,
        federal_agi: float,
        federal_taxable_income: float = None,
        state_adjustments: Dict[str, float] = None
    ) -> StateTaxResult:
        """
        Calculate state income tax.

        Args:
            federal_agi: Federal Adjusted Gross Income
            federal_taxable_income: Federal taxable income (after deductions)
            state_adjustments: State-specific adjustments

        Returns:
            StateTaxResult with state tax details
        """
        result = StateTaxResult(state=self.state)

        if not self.config:
            result.notes = f"State {self.state} not configured"
            return result

        if self.config.tax_type == StateTaxType.NONE:
            result.taxable_income = 0
            result.tax_liability = 0
            result.effective_rate = 0
            return result

        # Start with federal AGI
        state_agi = federal_agi

        # Apply state-specific adjustments
        if state_adjustments:
            for adj_name, adj_amount in state_adjustments.items():
                state_agi += adj_amount

        # Apply state standard deduction
        if self.filing_status == 'married_jointly':
            std_ded = self.config.standard_deduction_mfj
        else:
            std_ded = self.config.standard_deduction_single

        result.deductions_used = std_ded
        result.taxable_income = max(0, state_agi - std_ded)

        # Calculate tax
        if self.config.tax_type == StateTaxType.FLAT:
            result.tax_liability = result.taxable_income * self.config.flat_rate
            result.marginal_rate = self.config.flat_rate

            # Massachusetts millionaire tax
            if self.state == 'MA' and result.taxable_income > 1000000:
                excess = result.taxable_income - 1000000
                result.tax_liability += excess * 0.04

        elif self.config.tax_type == StateTaxType.PROGRESSIVE:
            tax = 0
            income = result.taxable_income

            for bracket in self.config.brackets:
                min_income, max_income, rate = bracket

                if income <= min_income:
                    break

                taxable_in_bracket = min(income, max_income) - min_income
                if taxable_in_bracket > 0:
                    tax += taxable_in_bracket * rate
                    result.marginal_rate = rate

            result.tax_liability = tax

        # Calculate effective rate
        if federal_agi > 0:
            result.effective_rate = result.tax_liability / federal_agi
        else:
            result.effective_rate = 0

        return result

    @classmethod
    def get_all_states(cls) -> List[str]:
        """Get list of all configured states"""
        return list(cls.STATE_CONFIGS.keys())

    @classmethod
    def get_no_tax_states(cls) -> List[str]:
        """Get list of states with no income tax"""
        return [state for state, config in cls.STATE_CONFIGS.items()
                if config.tax_type == StateTaxType.NONE]

    @classmethod
    def compare_states(
        cls,
        federal_agi: float,
        states: List[str] = None,
        filing_status: str = 'single'
    ) -> Dict[str, StateTaxResult]:
        """
        Compare tax liability across multiple states.

        Args:
            federal_agi: Federal AGI to use for comparison
            states: List of states to compare (default: all)
            filing_status: Filing status

        Returns:
            Dict of state -> StateTaxResult, sorted by tax liability
        """
        if states is None:
            states = cls.get_all_states()

        results = {}
        for state in states:
            calc = cls(state, filing_status)
            results[state] = calc.calculate(federal_agi)

        # Sort by tax liability
        return dict(sorted(results.items(), key=lambda x: x[1].tax_liability))
