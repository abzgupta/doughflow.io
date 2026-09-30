# DoughFlow Architecture

Technical reference for contributors: how the simulation engine, module
system, API, and frontend fit together. For setup, see the [README](../README.md).

---

## Project Overview

DoughFlow is a **financial flow simulator** that lets users model their entire financial picture as a flowchart. Users create nodes (income sources, accounts, investments, debts, expenses) and connect them with edges (money flows). The system simulates month-by-month financial progression over multiple years.

### Core Concept

```
Salary → Checking → Savings → Stocks
              ↓         ↓
           Mortgage   Emergency Fund
              ↓
          Student Loan
```

- **Nodes** = Financial entities (each has its own module with state)
- **Edges** = Money flows (fixed amount, percentage, or remainder)
- **Simulation** = Month-by-month calculation of balances, growth, interest, taxes

---

## Tech Stack

### Frontend
- **React 18** with functional components and hooks
- **ReactFlow v11** for the graph/flowchart visualization
- **Ant Design (antd)** for UI components
- **Axios** for API calls
- **Context API** (`GraphContext`) for state management

### Backend
- **FastAPI** (Python) REST API, served by uvicorn (interactive docs at `/docs`)
- **NumPy/Pandas** for calculations
- Custom module system for financial entities

---

## Directory Structure

```
doughflow_dot_io/
├── backend/
│   ├── app.py                    # FastAPI routes & API endpoints
│   ├── schemas.py                # Pydantic request models
│   ├── tests/                    # pytest suite
│   ├── ledger.log                # Transaction ledger (debug log)
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── graph_executor.py     # Core simulation engine
│   │   ├── cycle_detector.py     # Handles cycles in graph
│   │   ├── ledger.py             # Transaction logging system
│   │   ├── tax_settlement.py     # Yearly income tax totals and settlement
│   │   └── transactions.py       # Manual transaction handlers
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── base_module.py        # Abstract base class for all modules
│   │   ├── salary.py             # W2/1099 income
│   │   ├── savings_account.py    # Checking/savings/emergency fund
│   │   ├── stock_portfolio.py    # Stocks with dividends, capital gains
│   │   ├── four_oh_one_k.py      # 401(k) with employer match
│   │   ├── five_twenty_nine.py   # 529 education savings
│   │   ├── ira.py                # Traditional/Roth IRA
│   │   ├── real_estate.py        # Rental properties (original module)
│   │   ├── mortgage.py           # Home loans
│   │   ├── debt.py               # Student loans, car loans, credit cards
│   │   └── expense.py            # Fixed/variable/seasonal expenses
│   └── tax/
│       ├── __init__.py
│       ├── federal_tax.py        # Federal tax calculations
│       ├── state_tax.py          # State tax calculations
│       └── deductions.py         # Deduction calculator
│
├── src/
│   ├── App.js                    # Main app with layout
│   ├── App.css                   # Global styles
│   ├── context/
│   │   └── GraphContext.js       # React context for graph state
│   ├── hooks/
│   │   └── useGraphState.js      # Custom hook for simulation/save/load
│   └── components/
│       ├── flow/
│       │   ├── FlowCanvas.js     # ReactFlow canvas wrapper
│       │   └── FlowToolbar.js    # Node palette for adding nodes
│       ├── nodes/
│       │   └── BaseNode.js       # Universal node component
│       ├── forms/
│       │   ├── NodeConfigDrawer.js # Dynamic form based on module schema
│       │   └── EdgeConfigModal.js  # Edge configuration form
│       └── panels/
│           ├── SimulationPanel.js    # Simulation controls & results
│           ├── TransactionModal.js   # Manual transaction UI
│           ├── TaxSummaryPanel.js    # Tax summary
│           └── UserProfilePanel.js   # Tax profile settings
│
├── src/examples/sampleGraph.json # Example graph loaded on startup
├── package.json
└── README.md
```

---

## Key Backend APIs

### Simulation
```
POST /api/simulate
Body: { nodes, edges, user_profile, config }
Response: { success, snapshots[], final_net_worth, errors }
```

### Validation
```
POST /api/graph/validate
Body: { nodes, edges }
Response: { valid, errors, warnings, cycles }
```

### Manual Transactions (Interactive Mode)
```
POST /api/transaction
Body: { transaction_type, nodes, node_states, user_profile, year, month, params }
Response: { success, message, updated_balances, tax_implications, events }

POST /api/simulate/continue
Body: { nodes, edges, user_profile, config, resume_from_month, node_states }
Response: { success, snapshots[], final_net_worth }
```

### Ledger
```
POST /api/ledger/clear
Response: { success, message }
```

### Module Registry
```
GET /api/modules
Response: { module_type: { name, type, description, schema } }
```

---

## Module System

All financial modules inherit from `BaseModule` in `backend/modules/base_module.py`.

### Key Methods Each Module Implements:

```python
class SomeModule(BaseModule):
    @property
    def module_type(self) -> ModuleType: ...

    @property
    def flow_direction(self) -> FlowDirection: ...  # INFLOW, OUTFLOW, or BOTH

    @classmethod
    def get_config_schema(cls) -> Dict: ...  # JSON Schema for config

    def initialize(self, start_date: str) -> ModuleState: ...

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],      # {source_node_id: amount}
        available_for_outflow: float,   # Total available (balance + inflows)
        user_profile: Dict[str, Any]
    ) -> FlowResult: ...

    def is_active_for_date(self, year: int, month: int) -> bool: ...  # Scheduling
```

### Module Types Available:
1. **salary** - W2/1099 income with withholding
2. **savings_account** - Checking, savings, emergency fund, money market
3. **stock_portfolio** - Stocks with dividends, FIFO capital gains tracking
4. **four_oh_one_k** - 401(k) with employer match, vesting
5. **five_twenty_nine** - 529 education savings
6. **ira** - Traditional/Roth IRA
7. **real_estate** - Rental properties with depreciation
8. **mortgage** - Home loans with amortization
9. **debt** - Student loans, car loans, credit cards
10. **expense** - Fixed, variable, seasonal expenses

---

## Graph Executor Flow

The simulation runs in `backend/engine/graph_executor.py`:

1. **Initialize** all modules with `initialize(start_date)`
2. **For each month:**
   - Determine inactive nodes (past their `end_date`)
   - Process nodes by topological rank (handles cycles via convergence)
   - For each node:
     - Calculate inflows from previous nodes
     - Call `process_month()` on the module
     - Calculate outflows based on edges (fixed/percentage/remainder)
     - Record flows in snapshot
     - Record the module's `TaxInfo` and any tax realized by its outflows
   - Add the month's tax info to the running tax year
   - In December, and in the last simulated month, settle the year's taxes (see below)
   - Log to ledger
3. **Return** all snapshots with balances, flows, events, net worth

### Tax Settlement

Income taxes are settled once per calendar year by `backend/engine/tax_settlement.py`:

- Every month each module reports a `TaxInfo` (taxable income, deductions, capital
  gains, dividends, withholding). Money moved out of a traditional 401(k)/IRA records
  its taxable income and the 10% early withdrawal penalty (age < 59.5 from the user
  profile); selling shares to fund an outflow records realized gains. 529 outflows are
  treated as qualified and tax-free
- Salary income is wages (or self-employment income for 1099). Only federal and state
  income tax withholding counts toward what's already paid; FICA is not refundable
- Rental properties report rent net of their expenses (net rental losses aren't
  deducted in v1). A property with no rent is a primary residence: its mortgage interest
  and property tax are itemized, and a sale gain gets the $250k/$500k exclusion
- At the end of December (and of the last simulated month, for a partial year),
  `FederalTaxCalculator` and `StateTaxCalculator` compute the year's tax using the user
  profile (filing status, state, dependents for the child tax credit). State income tax
  and property tax feed the SALT deduction
- Tax + penalties − withholding is paid from the tax account with `apply_outflow`, or a
  refund is deposited with `apply_inflow`. The tax account is `config.tax_payment_node`,
  defaulting to the first savings/checking account. If the account can't cover the bill,
  the unpaid part is reported in an event; no money is created
- The settlement month's snapshot gets `tax_info['annual']` and an event such as
  `2026 taxes: owed $X, withheld $Y, paid $Z from Checking`
- `/api/simulate/step` runs one month without the rest of the year, so it doesn't settle.
  `/api/simulate/continue` only sees the months after the resume point for that year
- Not modeled yet: quarterly estimated payments, loss carryovers, credits other than the
  child tax credit

---

## Edge Types

Edges define how money flows between nodes:

```javascript
{
  source: "checking_1",
  target: "savings_1",
  data: {
    flowType: "fixed",      // "fixed", "percentage", or "remainder"
    amount: 1000,           // Dollar amount or percentage (0-100)
    frequency: "monthly",   // "monthly", "quarterly", "annually"
    priority: 1,            // Lower = higher priority
    condition: null         // Optional: { type: "threshold", source_balance_min: 10000 }
  }
}
```

---

## Node Scheduling (Start/End Dates)

Nodes can have optional start/end dates:

```javascript
{
  id: "car_loan_1",
  data: {
    moduleType: "debt",
    config: {
      name: "Car Loan",
      start_year: 2024,
      start_month: 1,
      end_year: 2027,
      end_month: 6,
      // ... other config
    }
  }
}
```

When a node is outside its active date range:
- It's added to `snapshot.inactive_nodes`
- The FlowCanvas dims the node and its edges
- No money flows to/from it

---

## Interactive Mode (Transactions)

Users can pause the simulation and execute manual transactions:

1. **Sell Stocks** - Sells shares using FIFO, calculates capital gains
2. **Pay Debt** - Pay off debt partially or fully from an account
3. **Transfer** - Move money between accounts

After a transaction:
- `nodeStates` is updated locally
- User can click "Continue Sim" to re-run from that point
- Or "Restart" to clear everything

---

## Transaction Ledger

Located at `backend/ledger.log`. Records:
- Simulation start/end
- Month-by-month balances
- Each node's processing details
- All money flows
- Manual transactions
- Errors

The ledger is cleared when:
- Running a new simulation (`/api/simulate`)
- Clicking "Restart" button (`/api/ledger/clear`)

---

## Frontend State Management

### GraphContext (`src/context/GraphContext.js`)

Central state using `useReducer`:

```javascript
{
  nodes: [],              // ReactFlow nodes
  edges: [],              // ReactFlow edges
  userProfile: {          // Tax profile
    filing_status: "married_jointly",
    state: "CA",
    age: 35,
    dependents: 2
  },
  simulationConfig: {
    start_year: 2024,
    start_month: 1,
    duration_months: 60
  },
  simulationResult: null, // After running simulation
  isSimulating: false,
  selectedNode: null,
  selectedEdge: null
}
```

### useGraphState Hook (`src/hooks/useGraphState.js`)

Provides:
- `runSimulation()` - Calls API and stores result
- `validateGraph()` - Validates before simulation
- `saveGraph()` - Downloads JSON file
- `loadGraphFromFile(file)` - Loads from JSON file
- `toApiFormat()` - Converts ReactFlow format to API format

---

## Architecture Notes

Open bugs are tracked in [GitHub issues](https://github.com/abzgupta/doughflow.io/issues).

- Each module's state is the single source of truth for its balance. Modules apply their own inflows, growth, and interest in `process_month`
- The executor sends money out along edges by calling `module.apply_outflow(amount, user_profile)`, and the target receives exactly what was paid out. Modules with sub-accounts override it (stocks use cash and then sell shares; the 401(k), IRA, and 529 use their withdrawal logic). Overrides whose withdrawals are taxable record it with `_record_realized_tax`, which the executor collects with `take_realized_tax_info()`
- Money from outside the edges (tax refunds) is added with `module.apply_inflow(amount)`
- Taxes are settled yearly inside the simulation (see [Tax Settlement](#tax-settlement)); `SalaryModule` balances are already net of withholding
- `node_balances` in snapshots mirrors module balances after outflows
- Net worth is the sum of module balances, skipping expense nodes: their balance is a running total of money already paid out of other accounts
- `available_for_outflow` is informational capacity, NOT a withdrawal request
- GraphContext's `setNodes`/`setEdges` do NOT support functional updates (no `prevState =>` pattern)
- After manual transactions, there are TWO sources of truth: snapshots (historical) and nodeStates (modified)

---

## Example Graph

`src/examples/sampleGraph.json` is loaded (and simulated) when the app starts, and
via **File → Load Example**. It is also the fixture for the backend API tests. It contains:
- $120k salary
- 401(k) with employer match
- Checking and emergency fund accounts
- Brokerage account ($25k stocks + $2k cash)
- Primary residence and rental property
- Student loan, car loan
- Daycare (ends Aug 2028), summer camp (Jun-Aug seasonal)
- Utilities

---

## Running the Application

See the [README](../README.md#quickstart).

### Debugging:
- Check `backend/ledger.log` for transaction history
- Backend prints debug info to the uvicorn console when simulating
- React DevTools for frontend state

---

## Common Tasks

### Adding a New Module Type:
1. Create `backend/modules/new_module.py`
2. Inherit from `BaseModule`
3. Implement required methods
4. Add to `backend/modules/__init__.py`
5. Add to `get_module_registry()` in `backend/app.py`
6. Add to `create_module_from_type()` factory in `backend/app.py`

### Adding a New Transaction Type:
1. Add handler in `backend/engine/transactions.py`
2. Add case in `/api/transaction` endpoint in `backend/app.py`
3. Add UI in `src/components/panels/TransactionModal.js`

### Debugging Simulation Issues:
1. Run simulation
2. Check `backend/ledger.log` for detailed flow
3. Look for unexpected balances or flows
4. Trace through `graph_executor.py` `_process_node()`

---

## User Profile Fields

```javascript
{
  filing_status: "single" | "married_jointly" | "married_separately" | "head_of_household",
  state: "CA" | "NY" | "TX" | ...,
  age: number,
  annual_salary: number,  // For reference
  dependents: number
}
```

---

## Simulation Config Fields

```javascript
{
  start_year: 2024,
  start_month: 1,        // 1-12
  duration_months: 60,   // Total months to simulate
  tax_payment_node: "checking_1"  // Optional: account taxes are paid from / refunded to
}
```

---

## File Save/Load Format

Saves as JSON with structure:
```javascript
{
  nodes: [...],
  edges: [...],
  userProfile: {...},
  simulationConfig: {...},
  savedAt: "ISO timestamp"
}
```

Downloaded as `doughflow-YYYY-MM-DD.json`

---

## Development Tips

1. **Run uvicorn with `--reload`** so Python changes are picked up
2. **Check ledger.log** for debugging simulation issues
3. **Balances**: Module state is the source of truth; `backend/tests/test_conservation.py` checks that flows never create or destroy money
4. **Inactive nodes**: Check `is_active_for_date()` and `snapshot.inactive_nodes`
5. **Flow priority**: Lower number = processed first
6. **Cycles**: Handled via iterative convergence in `_resolve_cycle_rank()`

---

## Frontend Pitfalls

Bugs that have bitten this codebase before and how they were fixed. **Read this before changing `GraphContext` or `SimulationPanel`.**

### Pitfall 1: Using Functional Updates with GraphContext's setNodes

**The wrong way:**
Tried to use React's functional update pattern with `graph.setNodes`:
```javascript
// WRONG - GraphContext doesn't support functional updates!
graph.setNodes(prevNodes => {
  const updatedNodes = prevNodes.map(node => { ... });
  return updatedNodes;
});
```

**Symptom:**
`graph.nodes.forEach is not a function` runtime error. The context's `setNodes` passes the argument directly to the reducer as `payload`, so it set `nodes` to the function itself instead of calling it.

**The Fix:**
Read `graph.nodes` directly and pass the resulting array:
```javascript
// CORRECT
const updatedNodes = graph.nodes.map(node => { ... });
graph.setNodes(updatedNodes);
```

**Takeaway:** The `GraphContext` uses `useReducer`, not `useState`. Its action creators (`setNodes`, `setEdges`, etc.) dispatch actions with the payload directly. They do NOT support functional updates like `useState`'s setter does. Always read state first, transform it, then pass the new value.

---

### Pitfall 2: Including graph.nodes in useEffect Dependency Array That Calls setNodes

**The wrong way:**
```javascript
React.useEffect(() => {
  // ... update nodes based on simulation snapshot
  const updatedNodes = graph.nodes.map(node => { ... });
  graph.setNodes(updatedNodes);
}, [currentMonth, result, graph.nodes, graph.setNodes]);  // graph.nodes in deps!
```

**Symptom:**
The UI numbers were "spasming" - rapidly flickering between values. This was an infinite render loop:
1. Effect runs → calls `setNodes()`
2. `graph.nodes` changes
3. Effect re-runs because `graph.nodes` is a dependency
4. Repeat forever

**The Fix:**
Use a `useRef` to track what's already been processed, and remove `graph.nodes` from dependencies:
```javascript
const lastProcessedRef = useRef({ month: null, resultId: null });

React.useEffect(() => {
  // Skip if already processed this state
  if (lastProcessedRef.current.month === currentMonth &&
      lastProcessedRef.current.resultId === resultId) {
    return;
  }

  // Read graph.nodes directly (not in deps)
  const updatedNodes = graph.nodes.map(...);
  graph.setNodes(updatedNodes);

  lastProcessedRef.current = { month: currentMonth, resultId };
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [currentMonth, result]);  // No graph.nodes!
```

**Takeaway:** If a `useEffect` both reads AND writes to the same state (like `graph.nodes`), you'll create an infinite loop if that state is in the dependency array. Use a ref to track processed state and exclude the state from deps. Add `eslint-disable-next-line` comment to acknowledge intentional omission.

---

### Pitfall 3: Snapshot Data Overwriting Transaction-Modified State

**The wrong way:**
After a manual transaction (e.g., paying off student loan), the node was correctly marked `isInactive: true`. But when stepping through the simulation, the useEffect would set `isInactive` based on `snapshot.inactive_nodes`, which doesn't know about manual transactions.

**Symptom:**
User pays off debt → node shows "Ended" and grays out → user steps forward one month → node becomes active again (ungrayed) because the old snapshot said it wasn't inactive.

**The Fix:**
When `hasModifications` is true:
1. Use balances from `nodeStates` (modified state), not from snapshot
2. Check if debt nodes have balance ≈ $0 and mark them inactive regardless of snapshot
3. Don't overwrite `nodeStates` with snapshot values

```javascript
// Use modified balance if we have modifications
let newBalance = snapshot.node_balances[node.id];
if (hasModifications && nodeStates[node.id]?.balance !== undefined) {
  newBalance = nodeStates[node.id].balance;
}

// Debt paid off = inactive, even if snapshot doesn't say so
const isPaidOffDebt = isDebtType && Math.abs(newBalance) < 0.01;
const isInactive = inactiveNodesFromSnapshot.includes(node.id) || isPaidOffDebt;
```

**Takeaway:** When supporting interactive modifications (transactions), you have TWO sources of truth: the original simulation snapshots and the modified `nodeStates`. Always check `hasModifications` and prefer the modified state. Simulation snapshots are historical and don't reflect user changes.

---

### Pitfall 4: Not Updating Edge Styles When Nodes Become Inactive

**The wrong way:**
Initially only updated node appearance when a debt was paid off, forgetting that connected edges also need to be grayed out.

**The Fix:**
FlowCanvas already had logic for this at lines 122-158, but it needed the node's `isInactive` status to be set correctly. Once the node status was correct, edges updated automatically.

**Takeaway:** The edge styling in `FlowCanvas.js` automatically updates based on `node.data.isInactive`. If edges aren't graying out, the problem is likely that the node's `isInactive` isn't being set correctly - fix the node state, not the edge logic.

---

### General Anti-Patterns to Avoid

1. **Don't assume context setters support functional updates** - Check the implementation
2. **Don't put state in useEffect deps if the effect modifies that state** - Use refs for tracking
3. **Don't forget there are two data sources after transactions** - Snapshots vs nodeStates
4. **Don't try to fix edge styling directly** - Fix the node's isInactive status instead
5. **Don't overwrite modified state with old snapshot data** - Check `hasModifications` first
