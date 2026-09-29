"""
DoughFlow API Server

Flask application providing endpoints for:
- Financial flow simulation
- Graph validation
- Tax calculations
- Legacy rental property calculations
"""

from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import numpy as np
import json

# Import modules
from modules import (
    BaseModule, ModuleType,
    RealEstateModule, SalaryModule, SavingsAccountModule,
    StockPortfolioModule, FourOhOneKModule, FiveTwentyNineModule,
    IRAModule, MortgageModule, DebtModule, ExpenseModule
)
from modules.base_module import MODULE_REGISTRY, create_module
from modules.real_estate import get_financial_table_summarized

# Import engine
from engine import GraphExecutor, ledger
from engine.graph_executor import FlowEdge, SimulationConfig

# Import tax
from tax import FederalTaxCalculator, FilingStatus, DeductionCalculator, StateTaxCalculator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'doughflow-financial-simulator-2024'
app.config['CORS_HEADERS'] = 'Content-Type'

cors = CORS(app, resources={r"/*": {"origins": "*"}})


# ============= Module Registry =============

def get_module_registry():
    """Get available module types and their schemas"""
    return {
        'salary': {
            'name': 'Salary/Income',
            'type': 'income_source',
            'description': 'W2 or 1099 income with withholding',
            'schema': SalaryModule.get_config_schema()
        },
        'savings_account': {
            'name': 'Savings/Checking Account',
            'type': 'account',
            'description': 'Interest-bearing bank accounts',
            'schema': SavingsAccountModule.get_config_schema()
        },
        'stock_portfolio': {
            'name': 'Stock Portfolio',
            'type': 'investment',
            'description': 'Stocks with dividends and capital gains',
            'schema': StockPortfolioModule.get_config_schema()
        },
        'four_oh_one_k': {
            'name': '401(k)',
            'type': 'investment',
            'description': 'Employer retirement account with matching',
            'schema': FourOhOneKModule.get_config_schema()
        },
        'five_twenty_nine': {
            'name': '529 Plan',
            'type': 'investment',
            'description': 'Education savings with tax benefits',
            'schema': FiveTwentyNineModule.get_config_schema()
        },
        'ira': {
            'name': 'IRA',
            'type': 'investment',
            'description': 'Traditional or Roth IRA',
            'schema': IRAModule.get_config_schema()
        },
        'real_estate': {
            'name': 'Real Estate',
            'type': 'investment',
            'description': 'Rental property investment',
            'schema': RealEstateModule.get_config_schema()
        },
        'mortgage': {
            'name': 'Mortgage',
            'type': 'debt',
            'description': 'Home loan with interest deduction',
            'schema': MortgageModule.get_config_schema()
        },
        'debt': {
            'name': 'Debt/Loan',
            'type': 'debt',
            'description': 'Student loan, car loan, credit card, or personal loan',
            'schema': DebtModule.get_config_schema() if DebtModule else {}
        },
        'expense': {
            'name': 'Expense',
            'type': 'expense',
            'description': 'Recurring expenses like childcare, utilities, subscriptions',
            'schema': ExpenseModule.get_config_schema() if ExpenseModule else {}
        }
    }


def create_module_from_type(module_type: str, node_id: str, config: dict) -> BaseModule:
    """Factory to create module instances from type string"""
    module_classes = {
        'salary': SalaryModule,
        'savings_account': SavingsAccountModule,
        'stock_portfolio': StockPortfolioModule,
        'four_oh_one_k': FourOhOneKModule,
        'five_twenty_nine': FiveTwentyNineModule,
        'ira': IRAModule,
        'real_estate': RealEstateModule,
        'mortgage': MortgageModule,
        'debt': DebtModule,
        'expense': ExpenseModule,
    }

    cls = module_classes.get(module_type)
    if not cls:
        raise ValueError(f"Unknown module type: {module_type}")

    return cls(node_id, config)


# ============= API Endpoints =============

@app.route('/api/modules', methods=['GET'])
@cross_origin()
def list_modules():
    """List available module types and their configuration schemas"""
    return jsonify(get_module_registry())


@app.route('/api/graph/validate', methods=['POST'])
@cross_origin()
def validate_graph():
    """
    Validate a financial flow graph.

    Request body:
    {
        "nodes": [
            {"id": "salary", "type": "salary", "config": {...}},
            {"id": "checking", "type": "savings_account", "config": {...}}
        ],
        "edges": [
            {"source": "salary", "target": "checking", "flow_type": "remainder", ...}
        ]
    }

    Response:
    {
        "valid": true/false,
        "errors": [...],
        "warnings": [...],
        "cycles": [...]
    }
    """
    data = request.json
    errors = []
    warnings = []
    cycles = []

    try:
        executor = GraphExecutor()

        # Add nodes
        nodes = data.get('nodes', [])
        for node in nodes:
            try:
                module = create_module_from_type(
                    node['type'],
                    node['id'],
                    node.get('config', {})
                )
                executor.add_node(node['id'], module)
            except Exception as e:
                errors.append(f"Invalid node '{node.get('id', 'unknown')}': {str(e)}")

        # Add edges
        edges = data.get('edges', [])
        for edge in edges:
            executor.add_edge(FlowEdge(
                source_id=edge['source'],
                target_id=edge['target'],
                flow_type=edge.get('flow_type', 'fixed'),
                amount=edge.get('amount', 0),
                frequency=edge.get('frequency', 'monthly'),
                priority=edge.get('priority', 0),
                condition=edge.get('condition')
            ))

        # Validate
        is_valid, validation_errors = executor.validate()
        errors.extend(validation_errors)

        # Detect cycles
        executor._build_cycle_detector()
        detected_cycles = executor._cycle_detector.find_all_cycles()
        for cycle in detected_cycles:
            cycles.append({
                'nodes': cycle.nodes,
                'warning': 'Cycle detected - will use iterative convergence'
            })
            warnings.append(f"Cycle detected: {' -> '.join(cycle.nodes)}")

    except Exception as e:
        errors.append(f"Validation error: {str(e)}")

    return jsonify({
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'cycles': cycles
    })


@app.route('/api/simulate', methods=['POST'])
@cross_origin()
def run_simulation():
    """
    Run financial flow simulation.

    Request body:
    {
        "nodes": [...],
        "edges": [...],
        "user_profile": {
            "filing_status": "married_jointly",
            "state": "CA",
            "age": 35,
            "annual_salary": 150000
        },
        "config": {
            "start_year": 2024,
            "start_month": 1,
            "duration_months": 120
        }
    }

    Response:
    {
        "success": true,
        "snapshots": [...],
        "annual_summaries": {...},
        "final_net_worth": 1234567.89,
        "errors": []
    }
    """
    data = request.json

    # Clear ledger at start of new simulation
    ledger.clear_ledger()

    try:
        executor = GraphExecutor()

        # Add nodes
        for node in data.get('nodes', []):
            module = create_module_from_type(
                node['type'],
                node['id'],
                node.get('config', {})
            )
            executor.add_node(node['id'], module)

        # Add edges
        for edge in data.get('edges', []):
            executor.add_edge(FlowEdge(
                source_id=edge['source'],
                target_id=edge['target'],
                flow_type=edge.get('flow_type', 'fixed'),
                amount=edge.get('amount', 0),
                frequency=edge.get('frequency', 'monthly'),
                priority=edge.get('priority', 0),
                condition=edge.get('condition')
            ))

        # Set user profile
        executor.set_user_profile(data.get('user_profile', {}))

        # Configure simulation
        config_data = data.get('config', {})
        config = SimulationConfig(
            start_year=config_data.get('start_year', 2024),
            start_month=config_data.get('start_month', 1),
            duration_months=config_data.get('duration_months', 120)
        )

        # Run simulation
        result = executor.simulate(config)

        # Debug: Print initial balances
        print("=== SIMULATION DEBUG ===")
        print(f"Nodes in executor: {list(executor.nodes.keys())}")
        if result.snapshots:
            first_snapshot = result.snapshots[0]
            print(f"First month balances: {first_snapshot.node_balances}")
            last_snapshot = result.snapshots[-1]
            print(f"Last month balances: {last_snapshot.node_balances}")
        print("========================")

        # Convert snapshots to JSON-serializable format
        snapshots = []
        for snap in result.snapshots:
            snapshots.append({
                'year': snap.year,
                'month': snap.month,
                'month_number': snap.month_number,
                'node_balances': snap.node_balances,
                'node_states': snap.node_states,  # Full module state for transactions
                'flows': snap.flows,
                'events': snap.events,
                'net_worth': snap.net_worth,
                'inactive_nodes': snap.inactive_nodes
            })

        return jsonify({
            'success': True,
            'snapshots': snapshots,
            'annual_summaries': result.annual_summaries,
            'final_net_worth': result.final_net_worth,
            'total_income': result.total_income,
            'total_expenses': result.total_expenses,
            'errors': result.errors
        })

    except Exception as e:
        import traceback
        ledger.log_error(str(e), {'traceback': traceback.format_exc()})
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 400


@app.route('/api/ledger/clear', methods=['POST'])
@cross_origin()
def clear_ledger():
    """
    Clear the transaction ledger log file.
    Called when restarting simulation from the beginning.
    """
    try:
        ledger.clear_ledger()
        return jsonify({
            'success': True,
            'message': 'Ledger cleared successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/tax/calculate', methods=['POST'])
@cross_origin()
def calculate_tax():
    """
    Calculate federal and state taxes.

    Request body:
    {
        "income": {
            "wages": 150000,
            "dividends_qualified": 5000,
            "capital_gains_long": 10000
        },
        "deductions": {
            "mortgage_interest": 15000,
            "salt": 12000,
            "charitable": 5000
        },
        "credits": {
            "child_tax_credit": 4000
        },
        "user_profile": {
            "filing_status": "married_jointly",
            "state": "CA",
            "age": 35
        },
        "withholding": 35000,
        "estimated_payments": 0
    }
    """
    data = request.json

    try:
        # Get user profile
        profile = data.get('user_profile', {})
        filing_status_str = profile.get('filing_status', 'single')

        # Map to FilingStatus enum
        filing_map = {
            'single': FilingStatus.SINGLE,
            'married_jointly': FilingStatus.MARRIED_JOINTLY,
            'mfj': FilingStatus.MARRIED_JOINTLY,
            'married_separately': FilingStatus.MARRIED_SEPARATELY,
            'head_of_household': FilingStatus.HEAD_OF_HOUSEHOLD,
        }
        filing_status = filing_map.get(filing_status_str, FilingStatus.SINGLE)

        # Calculate federal tax
        federal_calc = FederalTaxCalculator(filing_status)
        federal_result = federal_calc.calculate(
            income=data.get('income', {}),
            deductions=data.get('deductions', {}),
            credits=data.get('credits', {}),
            withholding=data.get('withholding', 0),
            estimated_payments=data.get('estimated_payments', 0),
            user_profile=profile
        )

        # Calculate state tax
        state = profile.get('state', 'CA')
        state_calc = StateTaxCalculator(state, filing_status_str)
        state_result = state_calc.calculate(federal_result.adjusted_gross_income)

        return jsonify({
            'federal': {
                'gross_income': federal_result.gross_income,
                'adjusted_gross_income': federal_result.adjusted_gross_income,
                'taxable_income': federal_result.taxable_income,
                'ordinary_income_tax': federal_result.ordinary_income_tax,
                'capital_gains_tax': federal_result.capital_gains_tax,
                'total_tax': federal_result.total_tax,
                'effective_rate': federal_result.effective_rate,
                'marginal_rate': federal_result.marginal_rate,
                'credits_applied': federal_result.credits_applied,
                'amt_liability': federal_result.amt_liability,
                'withholding': federal_result.withholding,
                'amount_owed': federal_result.amount_owed,
                'refund': federal_result.refund,
                'breakdown': federal_result.breakdown
            },
            'state': {
                'state': state_result.state,
                'taxable_income': state_result.taxable_income,
                'tax_liability': state_result.tax_liability,
                'effective_rate': state_result.effective_rate,
                'marginal_rate': state_result.marginal_rate
            },
            'total_tax': federal_result.total_tax + state_result.tax_liability,
            'total_effective_rate': (federal_result.total_tax + state_result.tax_liability) / federal_result.gross_income if federal_result.gross_income > 0 else 0
        })

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 400


@app.route('/api/tax/impact', methods=['POST'])
@cross_origin()
def calculate_tax_impact():
    """
    Calculate the tax impact of a financial decision.

    Request body:
    {
        "base_scenario": {...},  // Current tax situation
        "change": {
            "type": "401k_contribution",
            "amount": 5000
        }
    }
    """
    data = request.json

    try:
        base = data.get('base_scenario', {})
        change = data.get('change', {})
        profile = base.get('user_profile', {})

        # Calculate base tax
        filing_status_str = profile.get('filing_status', 'single')
        filing_map = {
            'single': FilingStatus.SINGLE,
            'married_jointly': FilingStatus.MARRIED_JOINTLY,
            'mfj': FilingStatus.MARRIED_JOINTLY,
        }
        filing_status = filing_map.get(filing_status_str, FilingStatus.SINGLE)

        federal_calc = FederalTaxCalculator(filing_status)
        base_result = federal_calc.calculate(
            income=base.get('income', {}),
            deductions=base.get('deductions', {}),
            credits=base.get('credits', {}),
            user_profile=profile
        )

        # Apply change to create modified scenario
        modified_income = dict(base.get('income', {}))
        modified_deductions = dict(base.get('deductions', {}))

        change_type = change.get('type')
        amount = change.get('amount', 0)

        if change_type == '401k_contribution':
            # 401k reduces taxable wages
            modified_income['wages'] = modified_income.get('wages', 0) - amount
        elif change_type == 'roth_contribution':
            # Roth doesn't affect current taxes
            pass
        elif change_type == 'traditional_ira':
            modified_deductions['traditional_ira'] = modified_deductions.get('traditional_ira', 0) + amount
        elif change_type == 'hsa':
            modified_deductions['hsa'] = modified_deductions.get('hsa', 0) + amount
        elif change_type == 'charitable':
            modified_deductions['charitable'] = modified_deductions.get('charitable', 0) + amount
        elif change_type == 'mortgage_payoff':
            # Eliminating mortgage reduces interest deduction
            modified_deductions['mortgage_interest'] = 0

        # Calculate modified tax
        modified_result = federal_calc.calculate(
            income=modified_income,
            deductions=modified_deductions,
            credits=base.get('credits', {}),
            user_profile=profile
        )

        tax_savings = base_result.total_tax - modified_result.total_tax

        return jsonify({
            'base_tax': base_result.total_tax,
            'modified_tax': modified_result.total_tax,
            'tax_savings': tax_savings,
            'effective_rate_change': base_result.effective_rate - modified_result.effective_rate,
            'marginal_rate': base_result.marginal_rate,
            'note': f"${amount:,.2f} {change_type} saves ${tax_savings:,.2f} in taxes"
        })

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 400


# ============= Interactive Simulation Endpoints =============

@app.route('/api/simulate/step', methods=['POST'])
@cross_origin()
def simulate_step():
    """
    Run a single month of simulation.
    Used for interactive step-by-step simulation.

    Request body:
    {
        "nodes": [...],
        "edges": [...],
        "user_profile": {...},
        "current_month": 1,  // 1-indexed month number
        "current_year": 2024,
        "node_states": {...}  // Optional: current state of nodes
    }
    """
    from engine.transactions import TransactionResult

    data = request.json

    try:
        executor = GraphExecutor()

        # Add nodes
        for node in data.get('nodes', []):
            module = create_module_from_type(
                node['type'],
                node['id'],
                node.get('config', {})
            )
            executor.add_node(node['id'], module)

        # Add edges
        for edge in data.get('edges', []):
            executor.add_edge(FlowEdge(
                source_id=edge['source'],
                target_id=edge['target'],
                flow_type=edge.get('flow_type', 'fixed'),
                amount=edge.get('amount', 0),
                frequency=edge.get('frequency', 'monthly'),
                priority=edge.get('priority', 0),
                condition=edge.get('condition')
            ))

        executor.set_user_profile(data.get('user_profile', {}))

        # Initialize or restore state
        node_states = data.get('node_states', {})
        current_year = data.get('current_year', 2024)
        current_month = data.get('current_month', 1)
        month_number = data.get('month_number', 1)

        # Build cycle detector
        executor._build_cycle_detector()

        # Initialize nodes
        start_date = f"{current_year}-{current_month:02d}"
        node_balances = {}
        for node_id, module in executor.nodes.items():
            if node_id in node_states:
                # Restore state
                node_balances[node_id] = node_states[node_id].get('balance', 0)
                state = module.get_state()
                state.balance = node_balances[node_id]
                module.set_state(state)
            else:
                # Initialize fresh
                initial_state = module.initialize(start_date)
                node_balances[node_id] = getattr(initial_state, 'balance', 0)

        # Execute single month
        config = SimulationConfig(
            start_year=current_year,
            start_month=current_month,
            duration_months=1
        )
        snapshot = executor._execute_month(
            month=current_month,
            year=current_year,
            month_number=month_number,
            node_balances=node_balances,
            config=config
        )

        return jsonify({
            'success': True,
            'snapshot': {
                'year': snapshot.year,
                'month': snapshot.month,
                'month_number': snapshot.month_number,
                'node_balances': snapshot.node_balances,
                'flows': snapshot.flows,
                'events': snapshot.events,
                'net_worth': snapshot.net_worth,
                'inactive_nodes': snapshot.inactive_nodes
            },
            'node_states': {
                node_id: {
                    'balance': module.get_state().balance,
                    'state': module.to_dict().get('state', {})
                }
                for node_id, module in executor.nodes.items()
            }
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 400


@app.route('/api/transaction', methods=['POST'])
@cross_origin()
def execute_transaction():
    """
    Execute a manual transaction during interactive simulation.

    Request body:
    {
        "transaction_type": "sell_stocks" | "pay_debt" | "transfer",
        "nodes": [...],  // Current node configurations
        "node_states": {...},  // Current balances
        "user_profile": {...},
        "year": 2024,
        "month": 6,
        "params": {
            // For sell_stocks:
            "source_node": "stocks_1",
            "amount": 50000,
            // For pay_debt:
            "source_node": "checking_1",
            "target_node": "car_loan_1",
            "amount": 18500,  // or "full" for full payoff
            // For transfer:
            "source_node": "savings_1",
            "target_node": "checking_1",
            "amount": 10000
        }
    }
    """
    from engine.transactions import (
        execute_sell_stocks, execute_pay_debt, execute_transfer,
        calculate_tax_on_gains, TransactionResult
    )

    data = request.json

    try:
        transaction_type = data.get('transaction_type')
        params = data.get('params', {})
        user_profile = data.get('user_profile', {})
        year = data.get('year', 2024)
        month = data.get('month', 1)
        node_states = data.get('node_states', {})

        # DEBUG: Print what we received for stocks
        print("=== TRANSACTION DEBUG ===")
        print(f"Transaction type: {transaction_type}")
        print(f"Params: {params}")
        source_node = params.get('source_node', 'unknown')
        if source_node in node_states:
            print(f"node_states[{source_node}]: {node_states[source_node]}")
        else:
            print(f"node_states keys: {list(node_states.keys())}")
            print(f"WARNING: {source_node} not in node_states!")

        # Create module instances with current state
        modules = {}
        for node in data.get('nodes', []):
            module = create_module_from_type(
                node['type'],
                node['id'],
                node.get('config', {})
            )
            # Restore state
            if node['id'] in node_states:
                node_state_data = node_states[node['id']]
                # Use restore_state if available (for stock portfolios, etc.)
                if hasattr(module, 'restore_state') and 'state' in node_state_data:
                    module.restore_state(node_state_data.get('state', {}))
                    # Also set balance at top level
                    module._state.balance = node_state_data.get('balance', module._state.balance)
                else:
                    # Fallback: just set balance
                    state = module.get_state()
                    state.balance = node_state_data.get('balance', 0)
                    # Restore additional state fields if present
                    for key, value in node_state_data.get('state', {}).items():
                        if hasattr(state, key):
                            setattr(state, key, value)
                    module.set_state(state)
            modules[node['id']] = module

        result = TransactionResult(success=False, message="Unknown transaction type")

        if transaction_type == 'sell_stocks':
            source_node = params.get('source_node')
            amount = params.get('amount', 0)
            destination_node = params.get('destination_node')

            if source_node not in modules:
                return jsonify({'success': False, 'error': f"Node {source_node} not found"}), 400

            # DEBUG: Print module state before sell
            stock_module = modules[source_node]
            print(f"Module state before sell:")
            print(f"  balance: {stock_module._state.balance}")
            print(f"  market_value: {getattr(stock_module._state, 'market_value', 'N/A')}")
            print(f"  shares: {getattr(stock_module._state, 'shares', 'N/A')}")
            print(f"  cash_balance: {getattr(stock_module._state, 'cash_balance', 'N/A')}")

            result = execute_sell_stocks(
                modules[source_node],
                amount,
                year,
                month
            )

            # Calculate tax implications
            if result.success and result.tax_implications:
                tax_estimate = calculate_tax_on_gains(
                    result.tax_implications.get('short_term_gains', 0),
                    result.tax_implications.get('long_term_gains', 0),
                    user_profile
                )
                result.tax_implications.update(tax_estimate)

                # Transfer proceeds to destination account if specified
                if destination_node and destination_node in modules:
                    proceeds = result.tax_implications.get('proceeds', 0)
                    if proceeds > 0:
                        dest_module = modules[destination_node]
                        dest_state = dest_module.get_state()
                        dest_state.balance = getattr(dest_state, 'balance', 0) + proceeds
                        dest_module.set_state(dest_state)
                        result.updated_balances[destination_node] = dest_state.balance
                        result.events.append(f"Deposited ${proceeds:,.2f} to {dest_module.display_name}")

                        # Also subtract from stock portfolio cash (proceeds went to destination)
                        stock_state = stock_module._state
                        stock_state.cash_balance -= proceeds
                        stock_state.balance = stock_state.market_value + stock_state.cash_balance
                        result.updated_balances[source_node] = stock_state.balance

        elif transaction_type == 'pay_debt':
            source_node = params.get('source_node')
            target_node = params.get('target_node')
            amount = params.get('amount', 0)

            if amount == 'full':
                amount = float('inf')

            if target_node not in modules:
                return jsonify({'success': False, 'error': f"Debt node {target_node} not found"}), 400

            source_module = modules.get(source_node) if source_node else None
            result = execute_pay_debt(
                modules[target_node],
                amount,
                source_module
            )

        elif transaction_type == 'transfer':
            source_node = params.get('source_node')
            target_node = params.get('target_node')
            amount = params.get('amount', 0)

            if source_node not in modules or target_node not in modules:
                return jsonify({'success': False, 'error': "Source or target node not found"}), 400

            result = execute_transfer(
                modules[source_node],
                modules[target_node],
                amount
            )

        # Get updated states for all affected nodes
        updated_states = {}
        for node_id, module in modules.items():
            state = module.get_state()
            updated_states[node_id] = {
                'balance': state.balance,
                'state': module.to_dict().get('state', {})
            }

        # Log transaction to ledger
        ledger.log_transaction(
            transaction_type=transaction_type,
            params=params,
            result={
                'success': result.success,
                'message': result.message,
                'updated_balances': result.updated_balances,
                'tax_implications': result.tax_implications
            },
            year=year,
            month=month
        )

        return jsonify({
            'success': result.success,
            'message': result.message,
            'updated_balances': result.updated_balances,
            'tax_implications': result.tax_implications,
            'events': result.events,
            'node_states': updated_states
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 400


@app.route('/api/simulate/continue', methods=['POST'])
@cross_origin()
def continue_simulation():
    """
    Continue simulation from a specific month with modified state.
    Used after executing manual transactions.

    Request body:
    {
        "nodes": [...],
        "edges": [...],
        "user_profile": {...},
        "config": {
            "start_year": 2024,
            "start_month": 1,
            "duration_months": 120
        },
        "resume_from_month": 25,  // 1-indexed month to resume from
        "node_states": {...}  // Current state at resume point
    }
    """
    data = request.json

    try:
        executor = GraphExecutor()

        # Add nodes
        for node in data.get('nodes', []):
            module = create_module_from_type(
                node['type'],
                node['id'],
                node.get('config', {})
            )
            executor.add_node(node['id'], module)

        # Add edges
        for edge in data.get('edges', []):
            executor.add_edge(FlowEdge(
                source_id=edge['source'],
                target_id=edge['target'],
                flow_type=edge.get('flow_type', 'fixed'),
                amount=edge.get('amount', 0),
                frequency=edge.get('frequency', 'monthly'),
                priority=edge.get('priority', 0),
                condition=edge.get('condition')
            ))

        executor.set_user_profile(data.get('user_profile', {}))

        # Configuration
        config_data = data.get('config', {})
        config = SimulationConfig(
            start_year=config_data.get('start_year', 2024),
            start_month=config_data.get('start_month', 1),
            duration_months=config_data.get('duration_months', 120)
        )

        resume_from = data.get('resume_from_month', 1)
        node_states = data.get('node_states', {})

        # Build cycle detector
        executor._build_cycle_detector()

        # Calculate the year/month for resume point
        total_months_from_start = resume_from - 1
        resume_year = config.start_year + (config.start_month - 1 + total_months_from_start) // 12
        resume_month = ((config.start_month - 1 + total_months_from_start) % 12) + 1

        # Initialize nodes with provided state
        start_date = f"{config.start_year}-{config.start_month:02d}"
        node_balances = {}
        for node_id, module in executor.nodes.items():
            if node_id in node_states:
                node_balances[node_id] = node_states[node_id].get('balance', 0)
                state = module.get_state()
                state.balance = node_balances[node_id]
                # Restore additional state
                for key, value in node_states[node_id].get('state', {}).items():
                    if hasattr(state, key):
                        setattr(state, key, value)
                module.set_state(state)
            else:
                initial_state = module.initialize(start_date)
                node_balances[node_id] = getattr(initial_state, 'balance', 0)

        # Run simulation from resume point to end
        snapshots = []
        current_year = resume_year
        current_month = resume_month

        for month_number in range(resume_from, config.duration_months + 1):
            snapshot = executor._execute_month(
                month=current_month,
                year=current_year,
                month_number=month_number,
                node_balances=node_balances,
                config=config
            )
            snapshots.append({
                'year': snapshot.year,
                'month': snapshot.month,
                'month_number': snapshot.month_number,
                'node_balances': snapshot.node_balances,
                'flows': snapshot.flows,
                'events': snapshot.events,
                'net_worth': snapshot.net_worth,
                'inactive_nodes': snapshot.inactive_nodes
            })

            # Advance month
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        final_net_worth = snapshots[-1]['net_worth'] if snapshots else 0

        return jsonify({
            'success': True,
            'snapshots': snapshots,
            'final_net_worth': final_net_worth,
            'resumed_from_month': resume_from
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 400


# ============= Legacy Endpoint =============

@app.route('/get_financial_table_summarized', methods=['POST', 'OPTIONS'])
@cross_origin()
def get_financial_table_summarized_endpoint():
    """Legacy endpoint for rental property calculations"""
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200

    property_list = request.json.get('property_list', [])

    try:
        rental_df = get_financial_table_summarized(property_list)
        rental_df = rental_df.replace([np.inf, -np.inf], np.finfo(np.float64).max)
        response = rental_df.to_dict(orient='records')
        return jsonify(response)
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 400


# ============= Health Check =============

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'modules_available': list(get_module_registry().keys())
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
