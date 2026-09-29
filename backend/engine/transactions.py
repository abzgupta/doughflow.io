"""
Manual Transaction Handler

Handles user-initiated transactions during interactive simulation:
- Sell stocks (with capital gains calculation)
- Pay off debt (partial or full)
- Transfer between accounts
"""

from typing import Dict, Any, Tuple, List
from dataclasses import dataclass, field


@dataclass
class TransactionResult:
    """Result of executing a manual transaction"""
    success: bool
    message: str
    updated_balances: Dict[str, float] = field(default_factory=dict)
    tax_implications: Dict[str, Any] = field(default_factory=dict)
    events: List[str] = field(default_factory=list)


def execute_sell_stocks(
    stock_module: Any,
    amount: float,
    year: int,
    month: int
) -> TransactionResult:
    """
    Sell stocks from a portfolio.

    Args:
        stock_module: StockPortfolioModule instance
        amount: Dollar amount to sell
        year: Current simulation year
        month: Current simulation month

    Returns:
        TransactionResult with proceeds and capital gains info
    """
    result = TransactionResult(success=False, message="")

    state = stock_module.get_state()
    current_value = getattr(state, 'balance', 0)

    if amount > current_value:
        result.message = f"Cannot sell ${amount:,.2f} - only ${current_value:,.2f} available"
        return result

    # Sell shares worth the specified dollar amount
    if hasattr(stock_module, 'sell_shares'):
        # Use the module's sell method (takes dollar amount, uses FIFO)
        sale_result = stock_module.sell_shares(amount)

        total_gains = sale_result.get('short_term_gains', 0) + sale_result.get('long_term_gains', 0)
        result.success = True
        result.message = f"Sold ${sale_result.get('proceeds', amount):,.2f} worth of stocks"
        result.updated_balances[stock_module.node_id] = stock_module.get_state().balance
        result.tax_implications = {
            'proceeds': sale_result.get('proceeds', amount),
            'cost_basis_sold': sale_result.get('cost_basis_sold', 0),
            'short_term_gains': sale_result.get('short_term_gains', 0),
            'long_term_gains': sale_result.get('long_term_gains', 0),
            'total_gains': total_gains,
        }
        result.events.append(f"Sold stocks: ${sale_result.get('proceeds', amount):,.2f} (gains: ${total_gains:,.2f})")
    else:
        # Fallback: simple balance reduction
        state.balance -= amount
        stock_module.set_state(state)

        result.success = True
        result.message = f"Sold ${amount:,.2f} worth of stocks"
        result.updated_balances[stock_module.node_id] = state.balance
        result.tax_implications = {
            'proceeds': amount,
            'estimated_gains': amount * 0.2,  # Rough estimate
        }
        result.events.append(f"Sold stocks: ${amount:,.2f}")

    return result


def execute_pay_debt(
    debt_module: Any,
    amount: float,
    source_module: Any = None
) -> TransactionResult:
    """
    Pay off debt (partial or full).

    Args:
        debt_module: DebtModule or MortgageModule instance
        amount: Amount to pay (use float('inf') for full payoff)
        source_module: Optional source account to deduct from

    Returns:
        TransactionResult with payment details
    """
    result = TransactionResult(success=False, message="")

    state = debt_module.get_state()
    current_balance = abs(getattr(state, 'balance', 0))

    if current_balance <= 0:
        result.message = "Debt is already paid off"
        result.success = True
        return result

    # Determine actual payment amount
    actual_payment = min(amount, current_balance)

    # Check source has enough funds
    if source_module:
        source_state = source_module.get_state()
        source_balance = getattr(source_state, 'balance', 0)
        if source_balance < actual_payment:
            result.message = f"Insufficient funds: need ${actual_payment:,.2f}, have ${source_balance:,.2f}"
            return result

        # Deduct from source
        source_state.balance -= actual_payment
        source_module.set_state(source_state)
        result.updated_balances[source_module.node_id] = source_state.balance

    # Apply payment to debt
    new_balance = current_balance - actual_payment
    state.balance = -new_balance  # Debt is stored as negative

    # Update debt-specific fields if available
    if hasattr(state, 'current_balance'):
        state.current_balance = new_balance
    if hasattr(state, 'is_paid_off'):
        state.is_paid_off = new_balance <= 0

    debt_module.set_state(state)

    result.success = True
    result.updated_balances[debt_module.node_id] = state.balance

    if new_balance <= 0:
        result.message = f"Paid off {debt_module.display_name} in full (${actual_payment:,.2f})"
        result.events.append(f"PAID OFF: {debt_module.display_name}")
    else:
        result.message = f"Paid ${actual_payment:,.2f} toward {debt_module.display_name} (${new_balance:,.2f} remaining)"
        result.events.append(f"Debt payment: ${actual_payment:,.2f} to {debt_module.display_name}")

    return result


def execute_transfer(
    source_module: Any,
    target_module: Any,
    amount: float
) -> TransactionResult:
    """
    Transfer funds between accounts.

    Args:
        source_module: Source module (must have positive balance)
        target_module: Target module
        amount: Amount to transfer

    Returns:
        TransactionResult with transfer details
    """
    result = TransactionResult(success=False, message="")

    source_state = source_module.get_state()
    source_balance = getattr(source_state, 'balance', 0)

    if amount > source_balance:
        result.message = f"Insufficient funds: need ${amount:,.2f}, have ${source_balance:,.2f}"
        return result

    # Deduct from source
    source_state.balance -= amount
    source_module.set_state(source_state)

    # Add to target
    target_state = target_module.get_state()
    target_state.balance = getattr(target_state, 'balance', 0) + amount
    target_module.set_state(target_state)

    result.success = True
    result.message = f"Transferred ${amount:,.2f} from {source_module.display_name} to {target_module.display_name}"
    result.updated_balances[source_module.node_id] = source_state.balance
    result.updated_balances[target_module.node_id] = target_state.balance
    result.events.append(f"Transfer: ${amount:,.2f} {source_module.node_id} → {target_module.node_id}")

    return result


def calculate_tax_on_gains(
    short_term_gains: float,
    long_term_gains: float,
    user_profile: Dict[str, Any]
) -> Dict[str, float]:
    """
    Estimate tax liability on capital gains.

    Args:
        short_term_gains: Short-term capital gains (taxed as ordinary income)
        long_term_gains: Long-term capital gains (preferential rates)
        user_profile: User's tax profile

    Returns:
        Dict with estimated taxes
    """
    filing_status = user_profile.get('filing_status', 'single')

    # Simplified tax rates (2024)
    if filing_status == 'married_jointly':
        # Short-term (ordinary income) - assume 24% bracket
        short_term_rate = 0.24
        # Long-term - 15% for most married filers
        long_term_rate = 0.15
    else:
        short_term_rate = 0.22
        long_term_rate = 0.15

    short_term_tax = short_term_gains * short_term_rate
    long_term_tax = long_term_gains * long_term_rate

    # State tax estimate (if CA)
    state = user_profile.get('state', 'CA')
    state_rate = 0.093 if state == 'CA' else 0.05  # CA taxes cap gains as ordinary income
    state_tax = (short_term_gains + long_term_gains) * state_rate

    return {
        'short_term_federal': short_term_tax,
        'long_term_federal': long_term_tax,
        'state_tax': state_tax,
        'total_estimated_tax': short_term_tax + long_term_tax + state_tax,
        'net_after_tax': (short_term_gains + long_term_gains) - (short_term_tax + long_term_tax + state_tax)
    }
