"""
Yearly income tax settlement for the simulation.

Modules report what they earned or deducted each month in a TaxInfo; money
moved out of retirement accounts and brokerages reports taxable withdrawals,
penalties and realized gains. TaxTracker adds all of it up per calendar year
and, at the end of December (or of the last simulated month), computes
federal + state tax with the tax calculators. The difference from what
paychecks already withheld is paid out of (or refunded into) a cash account.

v1 limits: no quarterly estimated payments, no passive-loss or capital-loss
carryovers, and credits are limited to the child tax credit from the user
profile's dependents.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from tax import FederalTaxCalculator, FilingStatus, StateTaxCalculator

FILING_STATUS_MAP = {
    'single': FilingStatus.SINGLE,
    'married_jointly': FilingStatus.MARRIED_JOINTLY,
    'mfj': FilingStatus.MARRIED_JOINTLY,
    'married_separately': FilingStatus.MARRIED_SEPARATELY,
    'head_of_household': FilingStatus.HEAD_OF_HOUSEHOLD,
}

# Module deduction keys -> FederalTaxCalculator deduction keys
FEDERAL_DEDUCTION_KEYS = {
    'ira_deduction': 'traditional_ira',
    'traditional_ira': 'traditional_ira',
    'hsa': 'hsa',
    'student_loan_interest': 'student_loan_interest',
    'mortgage_interest': 'mortgage_interest',
    'salt': 'salt',
    'property_tax': 'property_tax',  # folded into SALT at settlement
    'charitable': 'charitable',
    'medical': 'medical',
}

CHILD_TAX_CREDIT = 2000  # per qualifying child (2024)
CAPITAL_LOSS_LIMIT = 3000  # net capital loss deductible against ordinary income
HOME_SALE_EXCLUSION = {FilingStatus.MARRIED_JOINTLY: 500000}
HOME_SALE_EXCLUSION_DEFAULT = 250000


@dataclass
class TaxYear:
    """Running totals of one calendar year's tax inputs"""
    year: int
    months: int = 0
    wages: float = 0.0
    self_employment: float = 0.0
    interest: float = 0.0
    other_income: float = 0.0              # retirement withdrawals, misc
    rental_by_node: Dict[str, float] = field(default_factory=dict)  # net of rental expenses
    home_sale_gains: float = 0.0           # primary residence, before the exclusion
    dividends_qualified: float = 0.0
    dividends_ordinary: float = 0.0
    capital_gains_short: float = 0.0
    capital_gains_long: float = 0.0
    deductions: Dict[str, float] = field(default_factory=dict)  # calculator keys
    state_deductions: float = 0.0          # e.g. 529 contributions
    tax_deferred: float = 0.0              # informational: 401(k)/IRA contributions
    federal_withheld: float = 0.0
    state_withheld: float = 0.0
    penalties: float = 0.0

    def add(self, node_id: str, module: Any, info: Any) -> None:
        """Add one TaxInfo reported by a module"""
        kind = type(module).__name__
        config = getattr(module, 'config', {}) or {}

        if kind == 'SalaryModule':
            if config.get('income_type') == '1099':
                self.self_employment += info.taxable_income
            else:
                self.wages += info.taxable_income
            self._add_deductions(info.deductions)
        elif kind == 'SavingsAccountModule':
            self.interest += info.taxable_income
            self._add_deductions(info.deductions)
        elif kind == 'RealEstateModule' and _is_rental(config):
            # Schedule E: rent (and depreciation recapture) net of property expenses
            net = info.taxable_income - sum(info.deductions.values())
            self.rental_by_node[node_id] = self.rental_by_node.get(node_id, 0.0) + net
            self.capital_gains_short += info.capital_gains_short
            self.capital_gains_long += info.capital_gains_long
        elif kind == 'RealEstateModule':
            # Primary residence: interest and property tax are itemized; it was
            # never depreciated, so its sale is a (partly excluded) capital gain
            self._add_deductions({
                k: v for k, v in info.deductions.items() if k in ('mortgage_interest', 'property_tax')
            })
            self.home_sale_gains += info.capital_gains_short + info.capital_gains_long
        else:
            self.other_income += info.taxable_income
            self._add_deductions(info.deductions)

        if kind != 'RealEstateModule':
            self.capital_gains_short += info.capital_gains_short
            self.capital_gains_long += info.capital_gains_long
        self.dividends_qualified += info.qualified_dividends
        self.dividends_ordinary += info.ordinary_dividends
        self.tax_deferred += info.tax_deferred_income
        self.penalties += info.penalties

        # Only income tax withholding counts; info.withholding also includes FICA
        self.federal_withheld += info.federal_withholding
        self.state_withheld += info.state_withholding

    def _add_deductions(self, deductions: Dict[str, float]) -> None:
        for key, amount in deductions.items():
            if key == '529_state_deduction':
                self.state_deductions += amount
            elif key in FEDERAL_DEDUCTION_KEYS:
                target = FEDERAL_DEDUCTION_KEYS[key]
                self.deductions[target] = self.deductions.get(target, 0.0) + amount

    def compute(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Compute the year's federal and state income tax"""
        filing_str = user_profile.get('filing_status', 'single')
        filing_status = FILING_STATUS_MAP.get(filing_str, FilingStatus.SINGLE)

        # Net short- and long-term results; a net loss offsets up to $3k of ordinary income
        short, long_ = self.capital_gains_short, self.capital_gains_long
        exclusion = HOME_SALE_EXCLUSION.get(filing_status, HOME_SALE_EXCLUSION_DEFAULT)
        long_ += max(0.0, self.home_sale_gains - exclusion)
        capital_loss = 0.0
        if short + long_ < 0:
            capital_loss = min(CAPITAL_LOSS_LIMIT, -(short + long_))
            short = long_ = 0.0
        elif short < 0:
            long_, short = long_ + short, 0.0
        elif long_ < 0:
            short, long_ = short + long_, 0.0

        income = {
            'wages': self.wages,
            'self_employment': self.self_employment,
            'interest': self.interest,
            'dividends_ordinary': self.dividends_ordinary,
            'dividends_qualified': self.dividends_qualified,
            'capital_gains_short': short,
            'capital_gains_long': long_,
            # Passive rental losses aren't deductible against other income in v1
            'rental_income': sum(max(0.0, v) for v in self.rental_by_node.values()),
            'other_income': self.other_income - capital_loss,
        }
        deductions = dict(self.deductions)
        property_tax = deductions.pop('property_tax', 0.0)
        salt_paid = deductions.pop('salt', 0.0) + property_tax

        federal_calc = FederalTaxCalculator(filing_status, self.year)
        # First pass for AGI, which the state tax and credit phase-out need
        agi = federal_calc.calculate(income, deductions).adjusted_gross_income

        state = user_profile.get('state', 'CA')
        state_adjustments = {'529_contributions': -self.state_deductions} if self.state_deductions else None
        state_result = StateTaxCalculator(state, filing_str).calculate(agi, state_adjustments=state_adjustments)

        deductions['salt'] = salt_paid + state_result.tax_liability
        credits = {'child_tax_credit': _child_tax_credit(user_profile, filing_status, agi)}
        federal = federal_calc.calculate(
            income, deductions, credits,
            withholding=self.federal_withheld, user_profile=user_profile
        )

        total_tax = federal.total_tax + state_result.tax_liability + self.penalties
        withheld = self.federal_withheld + self.state_withheld
        return {
            'year': self.year,
            'months': self.months,
            'gross_income': federal.gross_income,
            'adjusted_gross_income': federal.adjusted_gross_income,
            'taxable_income': federal.taxable_income,
            'federal_tax': federal.total_tax,
            'state': state,
            'state_tax': state_result.tax_liability,
            'penalties': self.penalties,
            'total_tax': total_tax,
            'federal_withholding': self.federal_withheld,
            'state_withholding': self.state_withheld,
            'withholding': withheld,
            'tax_deferred': self.tax_deferred,
            # Positive: owed at filing; negative: refund
            'balance_due': total_tax - withheld,
        }


def _is_rental(config: Dict[str, Any]) -> bool:
    income = config.get('income_obj') or {}
    return (income.get('monthly_rent') or 0) > 0 or (income.get('other_monthly_income') or 0) > 0


def _child_tax_credit(user_profile: Dict[str, Any], filing_status: FilingStatus, agi: float) -> float:
    try:
        children = int(user_profile.get('dependents') or 0)
    except (TypeError, ValueError):
        children = 0
    if children <= 0:
        return 0.0
    threshold = 400000 if filing_status == FilingStatus.MARRIED_JOINTLY else 200000
    over = max(0.0, agi - threshold)
    reduction = 50 * -(-over // 1000)  # $50 per $1,000 (or part) over the threshold
    return max(0.0, CHILD_TAX_CREDIT * children - reduction)


class TaxTracker:
    """
    Collects TaxInfo during the simulation and settles each year.

    Per-node monthly TaxInfo is kept until the month closes (a node inside a
    cycle may be processed several times in one month; its last report wins).
    Tax realized by outflows is additive, since each outflow moves money.
    """

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.tax_year: Optional[TaxYear] = None
        self.total_taxes = 0.0
        self._month_reports: Dict[str, Tuple[Any, Any]] = {}
        self._month_realized: List[Tuple[str, Any, Any]] = []

    def record_report(self, node_id: str, module: Any, info: Any) -> None:
        if info is not None:
            self._month_reports[node_id] = (module, info)

    def record_realized(self, node_id: str, module: Any) -> None:
        info = module.take_realized_tax_info() if hasattr(module, 'take_realized_tax_info') else None
        if info is not None:
            self._month_realized.append((node_id, module, info))

    def close_month(self, year: int) -> TaxYear:
        """Fold this month's reports into the running year"""
        if self.tax_year is None or self.tax_year.year != year:
            self.tax_year = TaxYear(year=year)
        for node_id, (module, info) in self._month_reports.items():
            self.tax_year.add(node_id, module, info)
        for node_id, module, info in self._month_realized:
            self.tax_year.add(node_id, module, info)
        self.tax_year.months += 1
        self._month_reports = {}
        self._month_realized = []
        return self.tax_year

    def settle(
        self,
        nodes: Dict[str, Any],
        user_profile: Dict[str, Any],
        tax_payment_node: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], List[str], Optional[str]]:
        """
        Settle the running year: pay what's owed beyond withholding from the tax
        account, or deposit the refund into it.

        Returns (annual record, events, node_id whose balance changed or None).
        """
        tax_year = self.tax_year
        self.tax_year = None
        if tax_year is None:
            return {}, [], None

        annual = tax_year.compute(user_profile)
        self.total_taxes += annual['total_tax']
        due = round(annual['balance_due'], 2)
        node_id, problem = find_tax_account(nodes, tax_payment_node)
        account = nodes[node_id].display_name if node_id else None

        paid = refunded = unpaid = 0.0
        events = []
        if due > 0:
            if node_id:
                module = nodes[node_id]
                payable = min(due, max(0.0, module.get_state().balance))
                if payable > 0:
                    paid = module.apply_outflow(payable)
            unpaid = due - paid
        elif due < 0 and node_id:
            refunded = nodes[node_id].apply_inflow(-due)

        annual.update({
            'amount_owed': max(0.0, due),
            'refund': max(0.0, -due),
            'paid': paid,
            'refunded': refunded,
            'unpaid': unpaid,
            'paid_from': node_id,
        })

        summary = (f"{tax_year.year} taxes: owed ${annual['total_tax']:,.2f}, "
                   f"withheld ${annual['withholding']:,.2f}")
        if paid:
            summary += f", paid ${paid:,.2f} from {account}"
        if refunded:
            summary += f", refund ${refunded:,.2f} to {account}"
        events.append(summary)
        if due > 0 and unpaid > 0.005:
            reason = problem or f"{account} doesn't have enough cash"
            events.append(f"{tax_year.year} taxes: ${unpaid:,.2f} couldn't be paid ({reason})")
        elif due < 0 and not node_id:
            events.append(f"{tax_year.year} taxes: refund of ${-due:,.2f} not deposited ({problem})")

        return annual, events, node_id if (paid or refunded) else None


def find_tax_account(nodes: Dict[str, Any], configured: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Pick the cash account taxes are paid from: the configured node, else the
    first savings/checking account. Returns (node_id or None, problem).
    """
    if configured:
        module = nodes.get(configured)
        if module is None:
            return None, f"tax payment node '{configured}' not found"
        if module.module_type.value != 'account':
            return None, f"tax payment node '{configured}' isn't a cash account"
        return configured, None
    for node_id, module in nodes.items():
        if module.module_type.value == 'account':
            return node_id, None
    return None, "no savings or checking account to pay taxes from"
