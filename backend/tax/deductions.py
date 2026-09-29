"""
Tax Deductions Calculator

Handles itemized deductions, above-the-line deductions, and deduction optimization.
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum


class DeductionType(Enum):
    ABOVE_THE_LINE = "above_the_line"  # Reduces AGI
    ITEMIZED = "itemized"              # Part of Schedule A
    STANDARD = "standard"              # Standard deduction
    BUSINESS = "business"              # Business expenses


@dataclass
class Deduction:
    """A single deduction"""
    name: str
    amount: float
    deduction_type: DeductionType
    category: str
    limit: float = None
    phase_out_start: float = None
    phase_out_end: float = None


@dataclass
class DeductionResult:
    """Result of deduction calculation"""
    total_above_line: float = 0.0
    total_itemized: float = 0.0
    standard_deduction: float = 0.0
    use_itemized: bool = False
    final_deduction: float = 0.0
    agi_reduction: float = 0.0
    deductions_list: List[Deduction] = None
    optimization_notes: List[str] = None


class DeductionCalculator:
    """
    Calculate and optimize tax deductions.

    Handles:
    - Above-the-line deductions (IRA, HSA, SE health insurance, etc.)
    - Itemized deductions (SALT, mortgage interest, charitable, medical)
    - Standard deduction comparison
    - SALT cap ($10,000)
    - Mortgage interest limits ($750,000 acquisition debt)
    - Charitable contribution limits
    - Medical expense threshold (7.5% of AGI)
    """

    # 2024 Standard Deductions
    STANDARD_DEDUCTIONS = {
        'single': 14600,
        'married_jointly': 29200,
        'married_separately': 14600,
        'head_of_household': 21900,
    }

    # 2024 limits
    SALT_CAP = 10000
    MORTGAGE_DEBT_LIMIT = 750000
    CHARITABLE_AGI_LIMIT = 0.60  # 60% of AGI for cash
    HSA_LIMIT_SELF = 4150
    HSA_LIMIT_FAMILY = 8300
    HSA_CATCHUP = 1000
    IRA_LIMIT = 7000
    IRA_CATCHUP = 1000

    def __init__(self, filing_status: str = 'single', year: int = 2024):
        self.filing_status = filing_status
        self.year = year
        self.deductions: List[Deduction] = []

    def add_traditional_ira(self, contribution: float, has_employer_plan: bool, magi: float) -> Deduction:
        """
        Add Traditional IRA deduction.
        Phase-out applies if covered by employer plan.
        """
        limit = self.IRA_LIMIT
        deductible = min(contribution, limit)

        if has_employer_plan:
            # Phase-out for those with employer plans
            if self.filing_status == 'married_jointly':
                phase_out_start = 123000
                phase_out_end = 143000
            else:
                phase_out_start = 77000
                phase_out_end = 87000

            if magi >= phase_out_end:
                deductible = 0
            elif magi > phase_out_start:
                reduction = (magi - phase_out_start) / (phase_out_end - phase_out_start)
                deductible = deductible * (1 - reduction)

        deduction = Deduction(
            name="Traditional IRA",
            amount=deductible,
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category="retirement",
            limit=limit
        )
        self.deductions.append(deduction)
        return deduction

    def add_hsa(self, contribution: float, coverage: str = 'self', age: int = 30) -> Deduction:
        """Add HSA contribution deduction"""
        if coverage == 'family':
            limit = self.HSA_LIMIT_FAMILY
        else:
            limit = self.HSA_LIMIT_SELF

        if age >= 55:
            limit += self.HSA_CATCHUP

        deductible = min(contribution, limit)

        deduction = Deduction(
            name="HSA Contribution",
            amount=deductible,
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category="health",
            limit=limit
        )
        self.deductions.append(deduction)
        return deduction

    def add_student_loan_interest(self, interest: float, magi: float) -> Deduction:
        """Add student loan interest deduction (max $2,500)"""
        limit = 2500
        deductible = min(interest, limit)

        # Phase-out
        if self.filing_status == 'married_jointly':
            phase_out_start = 155000
            phase_out_end = 185000
        else:
            phase_out_start = 75000
            phase_out_end = 90000

        if magi >= phase_out_end:
            deductible = 0
        elif magi > phase_out_start:
            reduction = (magi - phase_out_start) / (phase_out_end - phase_out_start)
            deductible = deductible * (1 - reduction)

        deduction = Deduction(
            name="Student Loan Interest",
            amount=deductible,
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category="education",
            limit=limit
        )
        self.deductions.append(deduction)
        return deduction

    def add_self_employment_tax(self, se_tax: float) -> Deduction:
        """Add deduction for half of self-employment tax"""
        deductible = se_tax * 0.5

        deduction = Deduction(
            name="Self-Employment Tax Deduction",
            amount=deductible,
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category="self_employment"
        )
        self.deductions.append(deduction)
        return deduction

    def add_salt(self, state_income_tax: float, property_tax: float) -> Deduction:
        """Add State and Local Tax deduction (capped at $10,000)"""
        total = state_income_tax + property_tax
        deductible = min(total, self.SALT_CAP)

        deduction = Deduction(
            name="State and Local Taxes",
            amount=deductible,
            deduction_type=DeductionType.ITEMIZED,
            category="taxes",
            limit=self.SALT_CAP
        )
        self.deductions.append(deduction)
        return deduction

    def add_mortgage_interest(
        self,
        interest: float,
        acquisition_debt: float,
        is_primary_residence: bool = True
    ) -> Deduction:
        """Add mortgage interest deduction"""
        if not is_primary_residence:
            # Home equity interest not deductible unless used for home improvement
            deductible = 0
        elif acquisition_debt <= self.MORTGAGE_DEBT_LIMIT:
            deductible = interest
        else:
            # Pro-rate for debt over limit
            deductible = interest * (self.MORTGAGE_DEBT_LIMIT / acquisition_debt)

        deduction = Deduction(
            name="Mortgage Interest",
            amount=deductible,
            deduction_type=DeductionType.ITEMIZED,
            category="housing",
            limit=self.MORTGAGE_DEBT_LIMIT
        )
        self.deductions.append(deduction)
        return deduction

    def add_charitable(self, cash: float, non_cash: float, agi: float) -> Deduction:
        """Add charitable contribution deduction"""
        # Cash limited to 60% of AGI
        cash_limit = agi * 0.60
        cash_deductible = min(cash, cash_limit)

        # Non-cash limited to 30% of AGI
        non_cash_limit = agi * 0.30
        non_cash_deductible = min(non_cash, non_cash_limit)

        total = cash_deductible + non_cash_deductible

        deduction = Deduction(
            name="Charitable Contributions",
            amount=total,
            deduction_type=DeductionType.ITEMIZED,
            category="charitable"
        )
        self.deductions.append(deduction)
        return deduction

    def add_medical(self, medical_expenses: float, agi: float) -> Deduction:
        """Add medical expense deduction (over 7.5% of AGI)"""
        threshold = agi * 0.075
        deductible = max(0, medical_expenses - threshold)

        deduction = Deduction(
            name="Medical Expenses",
            amount=deductible,
            deduction_type=DeductionType.ITEMIZED,
            category="medical"
        )
        self.deductions.append(deduction)
        return deduction

    def calculate(self, agi: float = None) -> DeductionResult:
        """
        Calculate total deductions and determine itemized vs standard.

        Args:
            agi: Adjusted Gross Income (needed for some calculations)

        Returns:
            DeductionResult with deduction breakdown
        """
        result = DeductionResult()
        result.deductions_list = self.deductions
        result.optimization_notes = []

        # Sum above-the-line deductions
        above_line = [d for d in self.deductions if d.deduction_type == DeductionType.ABOVE_THE_LINE]
        result.total_above_line = sum(d.amount for d in above_line)
        result.agi_reduction = result.total_above_line

        # Sum itemized deductions
        itemized = [d for d in self.deductions if d.deduction_type == DeductionType.ITEMIZED]
        result.total_itemized = sum(d.amount for d in itemized)

        # Get standard deduction
        result.standard_deduction = self.STANDARD_DEDUCTIONS.get(self.filing_status, 14600)

        # Compare itemized vs standard
        if result.total_itemized > result.standard_deduction:
            result.use_itemized = True
            result.final_deduction = result.total_itemized
            result.optimization_notes.append(
                f"Itemizing saves ${result.total_itemized - result.standard_deduction:.2f}"
            )
        else:
            result.use_itemized = False
            result.final_deduction = result.standard_deduction
            gap = result.standard_deduction - result.total_itemized
            result.optimization_notes.append(
                f"Standard deduction is ${gap:.2f} more than itemized"
            )

        # Check for SALT cap impact
        salt = next((d for d in itemized if d.category == 'taxes'), None)
        if salt and salt.amount >= self.SALT_CAP:
            result.optimization_notes.append(
                "SALT deduction capped at $10,000"
            )

        return result

    def optimize_deductions(
        self,
        current_year_income: Dict[str, float],
        projected_next_year_income: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Provide deduction optimization suggestions.

        Returns suggestions for bunching deductions, timing contributions, etc.
        """
        suggestions = []

        current_itemized = sum(d.amount for d in self.deductions if d.deduction_type == DeductionType.ITEMIZED)
        standard = self.STANDARD_DEDUCTIONS.get(self.filing_status, 14600)

        # Bunching strategy
        if current_itemized * 2 > standard and current_itemized < standard:
            gap = standard - current_itemized
            suggestions.append({
                'type': 'bunching',
                'description': f"Consider bunching deductions. You're ${gap:.2f} short of itemizing. "
                              f"Prepaying next year's property taxes or making charitable contributions "
                              f"could push you over the threshold."
            })

        # Charitable timing
        charitable = next((d for d in self.deductions if d.category == 'charitable'), None)
        if charitable and current_itemized < standard:
            suggestions.append({
                'type': 'charitable_timing',
                'description': "Consider using a Donor Advised Fund to bunch multiple years of "
                              "charitable giving into one year to exceed the standard deduction."
            })

        # HSA maximization
        hsa = next((d for d in self.deductions if d.category == 'health' and d.name == 'HSA Contribution'), None)
        if hsa and hsa.amount < hsa.limit:
            remaining = hsa.limit - hsa.amount
            suggestions.append({
                'type': 'hsa',
                'description': f"You can contribute ${remaining:.2f} more to your HSA this year "
                              f"for additional tax savings."
            })

        return {
            'current_strategy': 'itemized' if current_itemized > standard else 'standard',
            'current_savings': max(current_itemized, standard),
            'suggestions': suggestions
        }

    def get_state_deduction(self, state: str, income: float, deductions: Dict[str, float]) -> float:
        """
        Calculate state-specific deduction.
        Many states use federal AGI as starting point with modifications.
        """
        # State-specific adjustments (simplified)
        state_adjustments = {
            'CA': {
                'standard_deduction': {'single': 5363, 'married_jointly': 10726},
                'itemized_allowed': True,
                'salt_deductible': False,  # No SALT on state return
            },
            'NY': {
                'standard_deduction': {'single': 8000, 'married_jointly': 16050},
                'itemized_allowed': True,
                'salt_deductible': False,
            },
            'TX': {
                'standard_deduction': 0,  # No state income tax
                'itemized_allowed': False,
            },
            'FL': {
                'standard_deduction': 0,  # No state income tax
                'itemized_allowed': False,
            },
        }

        state_info = state_adjustments.get(state, {
            'standard_deduction': {'single': 0, 'married_jointly': 0},
            'itemized_allowed': True,
            'salt_deductible': True,
        })

        if state_info['standard_deduction'] == 0:
            return 0

        standard = state_info['standard_deduction'].get(self.filing_status, 0)

        if not state_info['itemized_allowed']:
            return standard

        # Calculate state itemized (excluding SALT usually)
        itemized = sum(d.amount for d in self.deductions
                      if d.deduction_type == DeductionType.ITEMIZED
                      and (state_info.get('salt_deductible', True) or d.category != 'taxes'))

        return max(standard, itemized)
