"""
Stock Portfolio Module

Handles stock investments with dividends, capital gains, and cost basis tracking.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field

from .base_module import (
    BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo,
    register_module
)


@dataclass
class StockState(ModuleState):
    """State for stock portfolio"""
    market_value: float = 0.0
    cost_basis: float = 0.0
    shares: float = 0.0
    cash_balance: float = 0.0  # Uninvested cash in the portfolio
    ytd_dividends: float = 0.0
    ytd_contributions: float = 0.0
    ytd_withdrawals: float = 0.0
    ytd_realized_gains_short: float = 0.0
    ytd_realized_gains_long: float = 0.0
    ytd_realized_losses: float = 0.0
    # Track purchase lots for capital gains (FIFO)
    lots: List[Dict] = field(default_factory=list)  # [{shares, cost_per_share, months_held}]
    # Track pending sell orders for the month
    pending_sales: List[Dict] = field(default_factory=list)  # [{amount, reason}]


@register_module
class StockPortfolioModule(BaseModule):
    """
    Stock Portfolio Module

    Models stock investments with:
    - Expected annual return (growth)
    - Dividend yield (qualified dividends)
    - Cost basis tracking with FIFO
    - Short-term vs long-term capital gains
    - Automatic reinvestment option

    Config Parameters:
        name: Portfolio name
        initial_value: Starting portfolio value
        expected_annual_return: Expected annual return % (growth)
        dividend_yield: Annual dividend yield %
        dividend_reinvest: Whether to reinvest dividends
        expense_ratio: Annual expense ratio % (for funds/ETFs)
        monthly_volatility: Monthly volatility % (for realistic simulation)
    """

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.INVESTMENT

    @property
    def flow_direction(self) -> FlowDirection:
        return FlowDirection.BOTH

    @property
    def display_name(self) -> str:
        return self.config.get('name', 'Stock Portfolio')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Portfolio Name", "default": "Stock Portfolio"},
                "initial_value": {"type": "number", "title": "Initial Invested Value", "default": 0},
                "initial_cash": {"type": "number", "title": "Initial Cash Balance", "default": 0},
                "expected_annual_return": {"type": "number", "title": "Expected Annual Return %", "default": 7},
                "dividend_yield": {"type": "number", "title": "Dividend Yield %", "default": 2},
                "dividend_reinvest": {"type": "boolean", "title": "Reinvest Dividends", "default": False},
                "auto_invest_contributions": {"type": "boolean", "title": "Auto-Invest Contributions", "default": True},
                "expense_ratio": {"type": "number", "title": "Expense Ratio %", "default": 0.03},
                "monthly_volatility": {"type": "number", "title": "Monthly Volatility %", "default": 0},
                "target_cash_reserve": {"type": "number", "title": "Target Cash Reserve", "default": 0}
            },
            "required": ["name"]
        }

    def _validate_config(self) -> None:
        self.config.setdefault('name', 'Stock Portfolio')
        self.config.setdefault('initial_value', 0)
        self.config.setdefault('initial_cash', 0)
        self.config.setdefault('expected_annual_return', 7)
        self.config.setdefault('dividend_yield', 2)
        self.config.setdefault('dividend_reinvest', False)
        self.config.setdefault('auto_invest_contributions', True)
        self.config.setdefault('expense_ratio', 0.03)
        self.config.setdefault('monthly_volatility', 0)
        self.config.setdefault('target_cash_reserve', 0)

    def initialize(self, start_date: str) -> ModuleState:
        state = StockState()
        initial_value = self.config['initial_value']
        initial_cash = self.config.get('initial_cash', 0)

        state.market_value = initial_value
        state.cost_basis = initial_value
        state.cash_balance = initial_cash
        state.balance = initial_value + initial_cash  # Total portfolio value

        if initial_value > 0:
            # Assume $100/share for initial position
            state.shares = initial_value / 100
            state.lots = [{'shares': state.shares, 'cost_per_share': 100, 'months_held': 0}]

        self._state = state
        return state

    def _get_monthly_return(self) -> float:
        """Calculate expected monthly return (deterministic for now)"""
        annual_return = self.config['expected_annual_return'] / 100.0
        monthly_return = (1 + annual_return) ** (1/12) - 1
        return monthly_return

    def _calculate_dividend(self, market_value: float, month: int) -> float:
        """Calculate dividend payment (quarterly)"""
        if month not in [3, 6, 9, 12]:
            return 0

        annual_yield = self.config['dividend_yield'] / 100.0
        quarterly_dividend = market_value * (annual_yield / 4)
        return quarterly_dividend

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        # Ensure we have a properly initialized state
        if not isinstance(self._state, StockState):
            # Initialize if not already done
            self.initialize(f"{year}-{month:02d}")
        state = self._state
        result = FlowResult()
        tax_info = TaxInfo()

        # Reset YTD at start of year
        if month == 1:
            state.ytd_dividends = 0
            state.ytd_contributions = 0
            state.ytd_withdrawals = 0
            state.ytd_realized_gains_short = 0
            state.ytd_realized_gains_long = 0
            state.ytd_realized_losses = 0

        # Age all lots by 1 month
        for lot in state.lots:
            lot['months_held'] += 1

        # Process inflows (contributions go to cash first)
        total_contributions = sum(inflows.values())
        if total_contributions > 0:
            state.cash_balance += total_contributions
            state.ytd_contributions += total_contributions
            result.events.append(f"Received ${total_contributions:,.2f} contribution")

            # Auto-invest if enabled
            if self.config['auto_invest_contributions']:
                invest_amount = total_contributions
                target_reserve = self.config.get('target_cash_reserve', 0)
                if target_reserve > 0:
                    invest_amount = max(0, state.cash_balance - target_reserve)

                if invest_amount > 0:
                    self._buy_shares(state, invest_amount)
                    result.events.append(f"Auto-invested ${invest_amount:,.2f}")

        # Apply monthly growth to invested portion
        if state.market_value > 0:
            monthly_return = self._get_monthly_return()
            growth = state.market_value * monthly_return
            state.market_value += growth

            # Apply expense ratio
            monthly_expense = (self.config['expense_ratio'] / 100.0) / 12
            expense = state.market_value * monthly_expense
            state.market_value -= expense

        # Calculate dividend (quarterly)
        dividend = self._calculate_dividend(state.market_value, month)
        if dividend > 0:
            state.ytd_dividends += dividend

            if self.config['dividend_reinvest']:
                # Reinvest dividend by buying more shares
                self._buy_shares(state, dividend)
                result.events.append(f"Reinvested ${dividend:,.2f} dividend")
            else:
                # Dividend goes to cash balance
                state.cash_balance += dividend
                result.events.append(f"Received ${dividend:,.2f} dividend to cash")

        # Note: Outflows are handled by the graph executor based on edges.
        # The available_for_outflow parameter indicates capacity, not a withdrawal request.
        # Manual withdrawals should be done via the sell_shares() public method or transactions.

        # Tax info - dividends are qualified (lower tax rate)
        tax_info.qualified_dividends = dividend if not self.config['dividend_reinvest'] else 0

        # Update total balance (invested + cash)
        state.balance = state.market_value + state.cash_balance

        result.amount_received = total_contributions
        result.amount_sent = 0  # Outflows handled by executor based on edges
        result.new_state = state
        result.tax_info = tax_info

        self._state = state
        return result

    def _buy_shares(self, state: StockState, amount: float) -> Dict[str, Any]:
        """Buy shares with cash. Returns purchase details."""
        if amount <= 0 or amount > state.cash_balance:
            return {'shares': 0, 'price': 0, 'amount': 0}

        price_per_share = state.market_value / state.shares if state.shares > 0 else 100
        new_shares = amount / price_per_share

        state.shares += new_shares
        state.cost_basis += amount
        state.market_value += amount
        state.cash_balance -= amount

        state.lots.append({
            'shares': new_shares,
            'cost_per_share': price_per_share,
            'months_held': 0
        })

        return {
            'shares': new_shares,
            'price': price_per_share,
            'amount': amount
        }

    def _sell_shares(self, state: StockState, amount: float) -> Dict[str, Any]:
        """Sell shares worth the specified amount (FIFO). Returns sale details with gains."""
        if amount > state.market_value:
            amount = state.market_value

        if state.shares <= 0:
            return {'proceeds': 0, 'cost_basis_sold': 0, 'short_term_gains': 0, 'long_term_gains': 0}

        price_per_share = state.market_value / state.shares
        shares_to_sell = amount / price_per_share

        proceeds = 0
        cost_basis_sold = 0
        short_term_gains = 0
        long_term_gains = 0
        remaining_to_sell = shares_to_sell

        # FIFO: sell oldest lots first
        new_lots = []
        for lot in state.lots:
            if remaining_to_sell <= 0:
                new_lots.append(lot)
                continue

            if lot['shares'] <= remaining_to_sell:
                # Sell entire lot
                lot_proceeds = lot['shares'] * price_per_share
                lot_cost = lot['shares'] * lot['cost_per_share']
                gain = lot_proceeds - lot_cost

                proceeds += lot_proceeds
                cost_basis_sold += lot_cost

                # 12+ months = long-term capital gains
                if lot['months_held'] >= 12:
                    long_term_gains += gain
                else:
                    short_term_gains += gain

                remaining_to_sell -= lot['shares']
            else:
                # Partial lot sale
                lot_proceeds = remaining_to_sell * price_per_share
                lot_cost = remaining_to_sell * lot['cost_per_share']
                gain = lot_proceeds - lot_cost

                proceeds += lot_proceeds
                cost_basis_sold += lot_cost

                if lot['months_held'] >= 12:
                    long_term_gains += gain
                else:
                    short_term_gains += gain

                lot['shares'] -= remaining_to_sell
                new_lots.append(lot)
                remaining_to_sell = 0

        state.lots = new_lots
        state.shares -= shares_to_sell
        state.market_value -= proceeds
        state.cost_basis -= cost_basis_sold

        # Track realized gains/losses
        if short_term_gains >= 0:
            state.ytd_realized_gains_short += short_term_gains
        if long_term_gains >= 0:
            state.ytd_realized_gains_long += long_term_gains

        # Proceeds go to cash
        state.cash_balance += proceeds

        return {
            'proceeds': proceeds,
            'cost_basis_sold': cost_basis_sold,
            'short_term_gains': short_term_gains,
            'long_term_gains': long_term_gains
        }

    def sell_shares(self, amount: float) -> Dict[str, Any]:
        """
        Public method to sell shares worth the specified amount (FIFO method).
        Returns info about realized gains.
        """
        state = self._state if isinstance(self._state, StockState) else StockState()
        result = self._sell_shares(state, amount)
        # Update total balance after sale
        state.balance = state.market_value + state.cash_balance
        self._state = state
        return result

    def buy_shares(self, amount: float) -> Dict[str, Any]:
        """
        Public method to buy shares with available cash.
        Returns purchase details.
        """
        state = self._state if isinstance(self._state, StockState) else StockState()
        result = self._buy_shares(state, amount)
        self._state = state
        return result

    def apply_outflow(self, amount: float) -> float:
        """Pay out from cash first, then sell shares (FIFO) for the rest"""
        state = self._state if isinstance(self._state, StockState) else StockState()
        from_cash = min(amount, max(state.cash_balance, 0))
        state.cash_balance -= from_cash
        paid = from_cash

        shortfall = amount - from_cash
        if shortfall > 0:
            sale = self._sell_shares(state, shortfall)  # proceeds land in cash
            state.cash_balance -= sale['proceeds']
            paid += sale['proceeds']

        state.balance = state.market_value + state.cash_balance
        self._state = state
        return paid

    def get_cash_balance(self) -> float:
        """Get current cash balance in the portfolio."""
        state = self._state if isinstance(self._state, StockState) else StockState()
        return state.cash_balance

    def get_invested_value(self) -> float:
        """Get current market value of invested shares."""
        state = self._state if isinstance(self._state, StockState) else StockState()
        return state.market_value

    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        state = self._state if isinstance(self._state, StockState) else StockState()
        unrealized_gains = state.market_value - state.cost_basis
        total_realized_gains = state.ytd_realized_gains_short + state.ytd_realized_gains_long
        net_realized = total_realized_gains - state.ytd_realized_losses

        return {
            'market_value': state.market_value,
            'cash_balance': state.cash_balance,
            'total_value': state.market_value + state.cash_balance,
            'cost_basis': state.cost_basis,
            'unrealized_gains': unrealized_gains,
            'dividends_earned': state.ytd_dividends,
            'contributions': state.ytd_contributions,
            'withdrawals': state.ytd_withdrawals,
            'realized_gains_short': state.ytd_realized_gains_short,
            'realized_gains_long': state.ytd_realized_gains_long,
            'realized_losses': state.ytd_realized_losses,
            'net_realized_gains': net_realized
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize module to dictionary, including stock-specific state."""
        state = self._state if isinstance(self._state, StockState) else StockState()
        return {
            'node_id': self.node_id,
            'module_type': self.module_type.value,
            'config': self.config,
            'state': {
                'balance': state.balance,
                'market_value': state.market_value,
                'cost_basis': state.cost_basis,
                'shares': state.shares,
                'cash_balance': state.cash_balance,
                'ytd_dividends': state.ytd_dividends,
                'ytd_contributions': state.ytd_contributions,
                'ytd_withdrawals': state.ytd_withdrawals,
                'ytd_realized_gains_short': state.ytd_realized_gains_short,
                'ytd_realized_gains_long': state.ytd_realized_gains_long,
                'ytd_realized_losses': state.ytd_realized_losses,
                'lots': state.lots,
            }
        }

    def set_state(self, state: ModuleState) -> None:
        """Set module state, handling both ModuleState and StockState."""
        if isinstance(state, StockState):
            self._state = state
        else:
            # Convert basic ModuleState to StockState, preserving balance
            stock_state = StockState()
            stock_state.balance = state.balance
            # If balance is set but market_value isn't, assume all in market_value
            stock_state.market_value = state.balance
            stock_state.shares = state.balance / 100 if state.balance > 0 else 0
            stock_state.lots = [{'shares': stock_state.shares, 'cost_per_share': 100, 'months_held': 12}] if stock_state.shares > 0 else []
            self._state = stock_state

    def restore_state(self, state_dict: Dict[str, Any]) -> None:
        """Restore full state from dictionary (used by transactions)."""
        state = StockState()
        state.balance = state_dict.get('balance', 0)
        state.market_value = state_dict.get('market_value', state.balance)
        state.cost_basis = state_dict.get('cost_basis', state.market_value)
        state.shares = state_dict.get('shares', state.market_value / 100 if state.market_value > 0 else 0)
        state.cash_balance = state_dict.get('cash_balance', 0)
        state.ytd_dividends = state_dict.get('ytd_dividends', 0)
        state.ytd_contributions = state_dict.get('ytd_contributions', 0)
        state.ytd_withdrawals = state_dict.get('ytd_withdrawals', 0)
        state.ytd_realized_gains_short = state_dict.get('ytd_realized_gains_short', 0)
        state.ytd_realized_gains_long = state_dict.get('ytd_realized_gains_long', 0)
        state.ytd_realized_losses = state_dict.get('ytd_realized_losses', 0)
        state.lots = state_dict.get('lots', [])
        # If no lots but have shares, create a default lot
        if not state.lots and state.shares > 0:
            state.lots = [{'shares': state.shares, 'cost_per_share': state.cost_basis / state.shares if state.shares > 0 else 100, 'months_held': 12}]
        self._state = state
