# DoughFlow.io - Claude Handoff Document

**Last Updated:** 2026-02-03 (Session 2 - Added Lessons Learned)
**Purpose:** Detailed technical context for Claude Code sessions

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
- **Flask** (Python) REST API
- **NumPy/Pandas** for calculations
- Custom module system for financial entities

---

## Directory Structure

```
doughflow_dot_io/
├── backend/
│   ├── app.py                    # Flask routes & API endpoints
│   ├── ledger.log                # Transaction ledger (debug log)
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── graph_executor.py     # Core simulation engine
│   │   ├── cycle_detector.py     # Handles cycles in graph
│   │   ├── ledger.py             # Transaction logging system
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
│       │   └── CustomNode.js     # Universal node component
│       ├── forms/
│       │   ├── NodeConfigForm.js # Dynamic form based on module schema
│       │   └── EdgeConfigForm.js # Edge configuration form
│       └── panels/
│           ├── SimulationPanel.js    # Simulation controls & results
│           ├── TransactionModal.js   # Manual transaction UI
│           ├── UserProfilePanel.js   # Tax profile settings
│           └── ConfigPanel.js        # Simulation config
│
├── test-graph.json               # Sample graph for testing
├── package.json
└── README.md                     # Original (outdated) readme
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
   - Log to ledger
3. **Return** all snapshots with balances, flows, events, net worth

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

## Known Issues / Recent Fixes

### Fixed (2026-02-03 Session 2):
4. **Numbers "spasming" in UI** - `useEffect` in SimulationPanel had `graph.nodes` in dependency array while also calling `graph.setNodes()`, causing infinite render loop. Fixed by using `useRef` to track processed state and removing `graph.nodes` from deps.

5. **Paid-off debt nodes becoming active again when stepping** - After paying off debt via transaction, stepping through simulation would reset `isInactive` based on old snapshot data. Fixed by checking `hasModifications` and using modified `nodeStates` values instead of snapshot.

6. **Debt edges not graying out after payoff** - Node's `isInactive` wasn't being set on transaction payoff. Fixed by adding logic in `handleExecuteTransaction` to mark debt nodes as inactive when balance reaches $0.

### Fixed (2026-02-03 Session 1):
1. **Brokerage showing "Current: 0"** - `stock_portfolio.py` was incorrectly treating `available_for_outflow` as a withdrawal request, draining the entire balance. Fixed by removing automatic withdrawal logic.

2. **Summer camp node always visible** - `FlowCanvas.js` sync effect only checked node ID changes, not `isInactive` changes. Fixed by checking data property changes.

3. **Transaction sell_shares wrong signature** - `transactions.py` was passing wrong parameters to `sell_shares()`. Fixed.

### Architecture Notes:
- Modules handle their OWN internal state (inflows, growth, interest)
- The executor handles OUTFLOWS via edges (subtracts from node_balances)
- `available_for_outflow` is informational capacity, NOT a withdrawal request
- GraphContext's `setNodes`/`setEdges` do NOT support functional updates (no `prevState =>` pattern)
- After manual transactions, there are TWO sources of truth: snapshots (historical) and nodeStates (modified)

---

## Test Data

`test-graph.json` contains a sample financial scenario:
- $120k salary
- 401(k) with employer match
- Checking and emergency fund accounts
- Brokerage account ($25k stocks + $2k cash)
- Primary residence and rental property
- Student loan, car loan
- Daycare (ends Aug 2026), summer camp (Jun-Aug seasonal)
- Utilities

---

## Running the Application

### Backend:
```bash
cd backend
python app.py
# Runs on http://localhost:5000
```

### Frontend:
```bash
npm start
# Runs on http://localhost:3000
```

### Debug:
- Check `backend/ledger.log` for transaction history
- Backend prints debug info to console when simulating
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
  duration_months: 60    // Total months to simulate
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

## Tips for Future Sessions

1. **Always restart backend** after Python changes
2. **Check ledger.log** for debugging simulation issues
3. **Module state vs node_balances**: Modules track internal state, executor tracks balances for flows
4. **Inactive nodes**: Check `is_active_for_date()` and `snapshot.inactive_nodes`
5. **Flow priority**: Lower number = processed first
6. **Cycles**: Handled via iterative convergence in `_resolve_cycle_rank()`

---

## Mistakes Made & Lessons Learned (2026-02-03)

This section documents mistakes made during development and how they were resolved. **Read this before making changes to avoid repeating these errors.**

### Mistake 1: Using Functional Updates with GraphContext's setNodes

**What I Did Wrong:**
Tried to use React's functional update pattern with `graph.setNodes`:
```javascript
// WRONG - GraphContext doesn't support functional updates!
graph.setNodes(prevNodes => {
  const updatedNodes = prevNodes.map(node => { ... });
  return updatedNodes;
});
```

**What Happened:**
`graph.nodes.forEach is not a function` runtime error. The context's `setNodes` passes the argument directly to the reducer as `payload`, so it set `nodes` to the function itself instead of calling it.

**The Fix:**
Read `graph.nodes` directly and pass the resulting array:
```javascript
// CORRECT
const updatedNodes = graph.nodes.map(node => { ... });
graph.setNodes(updatedNodes);
```

**Lesson:** The `GraphContext` uses `useReducer`, not `useState`. Its action creators (`setNodes`, `setEdges`, etc.) dispatch actions with the payload directly. They do NOT support functional updates like `useState`'s setter does. Always read state first, transform it, then pass the new value.

---

### Mistake 2: Including graph.nodes in useEffect Dependency Array That Calls setNodes

**What I Did Wrong:**
```javascript
React.useEffect(() => {
  // ... update nodes based on simulation snapshot
  const updatedNodes = graph.nodes.map(node => { ... });
  graph.setNodes(updatedNodes);
}, [currentMonth, result, graph.nodes, graph.setNodes]);  // graph.nodes in deps!
```

**What Happened:**
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

**Lesson:** If a `useEffect` both reads AND writes to the same state (like `graph.nodes`), you'll create an infinite loop if that state is in the dependency array. Use a ref to track processed state and exclude the state from deps. Add `eslint-disable-next-line` comment to acknowledge intentional omission.

---

### Mistake 3: Snapshot Data Overwriting Transaction-Modified State

**What I Did Wrong:**
After a manual transaction (e.g., paying off student loan), the node was correctly marked `isInactive: true`. But when stepping through the simulation, the useEffect would set `isInactive` based on `snapshot.inactive_nodes`, which doesn't know about manual transactions.

**What Happened:**
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

**Lesson:** When supporting interactive modifications (transactions), you have TWO sources of truth: the original simulation snapshots and the modified `nodeStates`. Always check `hasModifications` and prefer the modified state. Simulation snapshots are historical and don't reflect user changes.

---

### Mistake 4: Not Updating Edge Styles When Nodes Become Inactive

**What I Did Wrong:**
Initially only updated node appearance when a debt was paid off, forgetting that connected edges also need to be grayed out.

**The Fix:**
FlowCanvas already had logic for this at lines 122-158, but it needed the node's `isInactive` status to be set correctly. Once the node status was correct, edges updated automatically.

**Lesson:** The edge styling in `FlowCanvas.js` automatically updates based on `node.data.isInactive`. If edges aren't graying out, the problem is likely that the node's `isInactive` isn't being set correctly - fix the node state, not the edge logic.

---

### General Anti-Patterns to Avoid

1. **Don't assume context setters support functional updates** - Check the implementation
2. **Don't put state in useEffect deps if the effect modifies that state** - Use refs for tracking
3. **Don't forget there are two data sources after transactions** - Snapshots vs nodeStates
4. **Don't try to fix edge styling directly** - Fix the node's isInactive status instead
5. **Don't overwrite modified state with old snapshot data** - Check `hasModifications` first

---

## Contact

Owner: abzgupta
