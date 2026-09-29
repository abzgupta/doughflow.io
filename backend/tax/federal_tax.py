"""
Federal Tax Calculator

Handles federal income tax calculation including:
- Progressive tax brackets
- Capital gains rates
- AMT calculation
- Tax credits
- Quarterly estimated taxes
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class FilingStatus(Enum):
    SINGLE = "single"
    MARRIED_JOINTLY = "married_jointly"
    MARRIED_SEPARATELY = "married_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"


@dataclass
class TaxBracket:
    """A single tax bracket"""
    min_income: float
    max_income: float
    rate: float  # As decimal (0.22 = 22%)


@dataclass
class TaxResult:
    """Result of tax calculation"""
    gross_income: float = 0.0
    adjusted_gross_income: float = 0.0
    taxable_income: float = 0.0
    ordinary_income_tax: float = 0.0
    capital_gains_tax: float = 0.0
    total_tax: float = 0.0
    effective_rate: float = 0.0
    marginal_rate: float = 0.0
    credits_applied: float = 0.0
    amt_liability: float = 0.0
    withholding: float = 0.0
    estimated_payments: float = 0.0
    amount_owed: float = 0.0
    refund: float = 0.0
    breakdown: Dict[str, float] = field(default_factory=dict)


class FederalTaxCalculator:
    """
    Federal tax calculator for 2024 tax year.

    Handles:
    - Progressive ordinary income tax brackets
    - Long-term capital gains rates (0%, 15%, 20%)
    - Qualified dividend rates
    - Net Investment Income Tax (NIIT)
    - Alternative Minimum Tax (AMT)
    - Common tax credits
    """

    # 2024 Federal Tax Brackets (Married Filing Jointly)
    BRACKETS_MFJ_2024 = [
        TaxBracket(0, 23200, 0.10),
        TaxBracket(23200, 94300, 0.12),
        TaxBracket(94300, 201050, 0.22),
        TaxBracket(201050, 383900, 0.24),
        TaxBracket(383900, 487450, 0.32),
        TaxBracket(487450, 731200, 0.35),
        TaxBracket(731200, float('inf'), 0.37),
    ]

    # 2024 Federal Tax Brackets (Single)
    BRACKETS_SINGLE_2024 = [
        TaxBracket(0, 11600, 0.10),
        TaxBracket(11600, 47150, 0.12),
        TaxBracket(47150, 100525, 0.22),
        TaxBracket(100525, 191950, 0.24),
        TaxBracket(191950, 243725, 0.32),
        TaxBracket(243725, 609350, 0.35),
        TaxBracket(609350, float('inf'), 0.37),
    ]

    # 2024 Standard Deductions
    STANDARD_DEDUCTIONS_2024 = {
        FilingStatus.SINGLE: 14600,
        FilingStatus.MARRIED_JOINTLY: 29200,
        FilingStatus.MARRIED_SEPARATELY: 14600,
        FilingStatus.HEAD_OF_HOUSEHOLD: 21900,
    }

    # Long-term capital gains brackets (MFJ 2024)
    LTCG_BRACKETS_MFJ_2024 = [
        TaxBracket(0, 94050, 0.0),
        TaxBracket(94050, 583750, 0.15),
        TaxBracket(583750, float('inf'), 0.20),
    ]

    # Long-term capital gains brackets (Single 2024)
    LTCG_BRACKETS_SINGLE_2024 = [
        TaxBracket(0, 47025, 0.0),
        TaxBracket(47025, 518900, 0.15),
        TaxBracket(518900, float('inf'), 0.20),
    ]

    # NIIT threshold
    NIIT_THRESHOLD_MFJ = 250000
    NIIT_THRESHOLD_SINGLE = 200000
    NIIT_RATE = 0.038

    # AMT exemptions (2024)
    AMT_EXEMPTION_MFJ = 133300
    AMT_EXEMPTION_SINGLE = 85700
    AMT_PHASE_OUT_MFJ = 1218700
    AMT_PHASE_OUT_SINGLE = 609350
    AMT_RATE_1 = 0.26
    AMT_RATE_2 = 0.28
    AMT_THRESHOLD = 232600  # Where 28% rate begins

    def __init__(self, filing_status: FilingStatus = FilingStatus.SINGLE, year: int = 2024):
        self.filing_status = filing_status
        self.year = year

    def _get_brackets(self) -> List[TaxBracket]:
        """Get tax brackets for filing status"""
        if self.filing_status == FilingStatus.MARRIED_JOINTLY:
            return self.BRACKETS_MFJ_2024
        else:
            return self.BRACKETS_SINGLE_2024

    def _get_ltcg_brackets(self) -> List[TaxBracket]:
        """Get long-term capital gains brackets for filing status"""
        if self.filing_status == FilingStatus.MARRIED_JOINTLY:
            return self.LTCG_BRACKETS_MFJ_2024
        else:
            return self.LTCG_BRACKETS_SINGLE_2024

    def _get_standard_deduction(self) -> float:
        """Get standard deduction for filing status"""
        return self.STANDARD_DEDUCTIONS_2024.get(self.filing_status, 14600)

    def _calculate_bracket_tax(self, income: float, brackets: List[TaxBracket]) -> Tuple[float, float]:
        """
        Calculate tax using progressive brackets.
        Returns (total_tax, marginal_rate)
        """
        if income <= 0:
            return 0, brackets[0].rate if brackets else 0

        total_tax = 0
        marginal_rate = 0

        for bracket in brackets:
            if income <= bracket.min_income:
                break

            taxable_in_bracket = min(income, bracket.max_income) - bracket.min_income
            if taxable_in_bracket > 0:
                total_tax += taxable_in_bracket * bracket.rate
                marginal_rate = bracket.rate

        return total_tax, marginal_rate

    def _calculate_capital_gains_tax(
        self,
        ordinary_income: float,
        short_term_gains: float,
        long_term_gains: float,
        qualified_dividends: float
    ) -> float:
        """Calculate capital gains tax"""
        # Short-term gains are taxed as ordinary income
        # Long-term gains and qualified dividends get preferential rates

        ltcg_brackets = self._get_ltcg_brackets()
        total_income = ordinary_income + short_term_gains

        # Long-term gains fill up from the top of ordinary income
        ltcg_amount = long_term_gains + qualified_dividends

        if ltcg_amount <= 0:
            return 0

        # Find where ordinary income lands in LTCG brackets
        ltcg_tax = 0
        remaining_ltcg = ltcg_amount

        for bracket in ltcg_brackets:
            if total_income >= bracket.max_income:
                continue

            space_in_bracket = bracket.max_income - max(total_income, bracket.min_income)
            gains_in_bracket = min(remaining_ltcg, space_in_bracket)

            if gains_in_bracket > 0:
                ltcg_tax += gains_in_bracket * bracket.rate
                remaining_ltcg -= gains_in_bracket
                total_income += gains_in_bracket

            if remaining_ltcg <= 0:
                break

        return ltcg_tax

    def _calculate_niit(
        self,
        magi: float,
        investment_income: float
    ) -> float:
        """Calculate Net Investment Income Tax (3.8%)"""
        threshold = self.NIIT_THRESHOLD_MFJ if self.filing_status == FilingStatus.MARRIED_JOINTLY else self.NIIT_THRESHOLD_SINGLE

        if magi <= threshold:
            return 0

        excess_magi = magi - threshold
        taxable_amount = min(excess_magi, investment_income)

        return taxable_amount * self.NIIT_RATE

    def _calculate_amt(
        self,
        taxable_income: float,
        itemized_deductions: Dict[str, float]
    ) -> float:
        """Calculate Alternative Minimum Tax"""
        # Start with taxable income
        amti = taxable_income

        # Add back certain itemized deductions
        amti += itemized_deductions.get('salt', 0)  # State and local taxes
        amti += itemized_deductions.get('misc_itemized', 0)

        # Calculate AMT exemption
        if self.filing_status == FilingStatus.MARRIED_JOINTLY:
            exemption = self.AMT_EXEMPTION_MFJ
            phase_out_start = self.AMT_PHASE_OUT_MFJ
        else:
            exemption = self.AMT_EXEMPTION_SINGLE
            phase_out_start = self.AMT_PHASE_OUT_SINGLE

        # Phase out exemption
        if amti > phase_out_start:
            phase_out = (amti - phase_out_start) * 0.25
            exemption = max(0, exemption - phase_out)

        # Calculate AMT
        amt_base = max(0, amti - exemption)

        if amt_base <= self.AMT_THRESHOLD:
            amt = amt_base * self.AMT_RATE_1
        else:
            amt = self.AMT_THRESHOLD * self.AMT_RATE_1 + (amt_base - self.AMT_THRESHOLD) * self.AMT_RATE_2

        return amt

    def calculate(
        self,
        income: Dict[str, float],
        deductions: Dict[str, float] = None,
        credits: Dict[str, float] = None,
        withholding: float = 0,
        estimated_payments: float = 0,
        user_profile: Dict[str, Any] = None
    ) -> TaxResult:
        """
        Calculate federal income tax.

        Args:
            income: Dict with income types:
                - wages: W2 wages
                - self_employment: 1099/business income
                - interest: Interest income
                - dividends_ordinary: Ordinary dividends
                - dividends_qualified: Qualified dividends
                - capital_gains_short: Short-term capital gains
                - capital_gains_long: Long-term capital gains
                - rental_income: Net rental income
                - other_income: Other taxable income

            deductions: Dict with deduction types:
                - traditional_ira: Traditional IRA contributions
                - hsa: HSA contributions
                - student_loan_interest: Student loan interest
                - salt: State and local taxes (capped at $10k)
                - mortgage_interest: Mortgage interest
                - charitable: Charitable contributions
                - medical: Medical expenses (over 7.5% AGI)

            credits: Dict with credit types:
                - child_tax_credit: Child tax credit
                - education_credit: Education credits
                - savers_credit: Retirement savings credit

            withholding: Total tax withheld during year
            estimated_payments: Quarterly estimated payments made
            user_profile: User info (dependents, age, etc.)

        Returns:
            TaxResult with full tax breakdown
        """
        if deductions is None:
            deductions = {}
        if credits is None:
            credits = {}
        if user_profile is None:
            user_profile = {}

        result = TaxResult()

        # Calculate gross income
        wages = income.get('wages', 0)
        self_employment = income.get('self_employment', 0)
        interest = income.get('interest', 0)
        dividends_ordinary = income.get('dividends_ordinary', 0)
        dividends_qualified = income.get('dividends_qualified', 0)
        capital_gains_short = income.get('capital_gains_short', 0)
        capital_gains_long = income.get('capital_gains_long', 0)
        rental_income = income.get('rental_income', 0)
        other_income = income.get('other_income', 0)

        result.gross_income = (wages + self_employment + interest +
                               dividends_ordinary + dividends_qualified +
                               capital_gains_short + capital_gains_long +
                               rental_income + other_income)

        # Calculate self-employment tax (if applicable)
        se_tax = 0
        if self_employment > 0:
            # Self-employment tax: 15.3% on 92.35% of SE income
            se_income = self_employment * 0.9235
            # Social Security portion (6.2% up to limit)
            ss_portion = min(se_income, 168600) * 0.124
            # Medicare portion (2.9% on all)
            medicare_portion = se_income * 0.029
            # Additional Medicare (0.9% over threshold)
            if se_income > 200000:
                medicare_portion += (se_income - 200000) * 0.009
            se_tax = ss_portion + medicare_portion

        # Above-the-line deductions (adjustments to income)
        above_line = 0
        above_line += deductions.get('traditional_ira', 0)
        above_line += deductions.get('hsa', 0)
        above_line += deductions.get('student_loan_interest', 0)
        above_line += se_tax * 0.5  # Deduction for half of SE tax

        result.adjusted_gross_income = result.gross_income - above_line

        # Itemized vs Standard deduction
        standard_deduction = self._get_standard_deduction()

        # Calculate itemized deductions
        salt = min(deductions.get('salt', 0), 10000)  # SALT cap
        mortgage_interest = deductions.get('mortgage_interest', 0)
        charitable = deductions.get('charitable', 0)
        medical = deductions.get('medical', 0)
        # Medical deduction only for amount over 7.5% of AGI
        medical_deductible = max(0, medical - result.adjusted_gross_income * 0.075)

        total_itemized = salt + mortgage_interest + charitable + medical_deductible

        # Use larger of itemized or standard
        if total_itemized > standard_deduction:
            total_deduction = total_itemized
            result.breakdown['deduction_type'] = 'itemized'
        else:
            total_deduction = standard_deduction
            result.breakdown['deduction_type'] = 'standard'

        result.breakdown['total_deduction'] = total_deduction

        # Calculate taxable income (excluding LTCG and qualified dividends for now)
        ordinary_income = (wages + self_employment + interest +
                          dividends_ordinary + capital_gains_short +
                          rental_income + other_income)

        result.taxable_income = max(0, ordinary_income - above_line - total_deduction)

        # Calculate ordinary income tax
        ordinary_tax, marginal_rate = self._calculate_bracket_tax(
            result.taxable_income, self._get_brackets()
        )
        result.ordinary_income_tax = ordinary_tax
        result.marginal_rate = marginal_rate

        # Calculate capital gains tax
        result.capital_gains_tax = self._calculate_capital_gains_tax(
            result.taxable_income,
            capital_gains_short,
            capital_gains_long,
            dividends_qualified
        )

        # Calculate NIIT
        investment_income = (interest + dividends_ordinary + dividends_qualified +
                            capital_gains_short + capital_gains_long)
        niit = self._calculate_niit(result.adjusted_gross_income, investment_income)
        result.breakdown['niit'] = niit

        # Calculate AMT
        if total_itemized > standard_deduction:
            amt = self._calculate_amt(result.taxable_income, {
                'salt': salt,
                'misc_itemized': 0
            })
            # AMT is the excess over regular tax
            regular_tax = result.ordinary_income_tax + result.capital_gains_tax
            result.amt_liability = max(0, amt - regular_tax)
        else:
            result.amt_liability = 0

        # Total tax before credits
        total_before_credits = (result.ordinary_income_tax +
                                result.capital_gains_tax +
                                se_tax + niit + result.amt_liability)

        # Apply credits
        child_credit = credits.get('child_tax_credit', 0)
        education_credit = credits.get('education_credit', 0)
        savers_credit = credits.get('savers_credit', 0)
        result.credits_applied = child_credit + education_credit + savers_credit

        result.total_tax = max(0, total_before_credits - result.credits_applied)

        # Calculate effective rate
        if result.gross_income > 0:
            result.effective_rate = result.total_tax / result.gross_income
        else:
            result.effective_rate = 0

        # Calculate amount owed or refund
        result.withholding = withholding
        result.estimated_payments = estimated_payments
        total_paid = withholding + estimated_payments

        if total_paid >= result.total_tax:
            result.refund = total_paid - result.total_tax
            result.amount_owed = 0
        else:
            result.amount_owed = result.total_tax - total_paid
            result.refund = 0

        # Store breakdown details
        result.breakdown['self_employment_tax'] = se_tax
        result.breakdown['above_line_deductions'] = above_line
        result.breakdown['itemized_deductions'] = total_itemized
        result.breakdown['standard_deduction'] = standard_deduction

        return result

    def calculate_estimated_tax(
        self,
        annual_income: Dict[str, float],
        quarter: int
    ) -> float:
        """
        Calculate quarterly estimated tax payment.

        Args:
            annual_income: Expected annual income
            quarter: Quarter (1-4)

        Returns:
            Recommended quarterly payment
        """
        result = self.calculate(annual_income)
        quarterly_payment = result.total_tax / 4

        return quarterly_payment
