# DoughFlow

**Model your finances as a flow of money, and simulate it month by month.**

DoughFlow lets you draw your financial life as a graph: income, accounts, investments,
property, debts and expenses are nodes, and the money moving between them is edges
("send $1,900 a month from salary to the 401(k)", "whatever's left in checking goes to
the brokerage"). The simulator then steps through the months and shows balances, flows,
and net worth, so you can ask *what if*: what if I buy a rental, pay off the car
early, or the daycare bill ends in 2028?

<!-- TODO: add a screenshot of the example graph -->

> **Status: early and experimental.** The engine has known correctness bugs (see
> [Known issues](#known-issues)), so treat the numbers as illustrative. Contributions welcome!

## Features

- Drag-and-drop graph editor (React Flow) with 10 building blocks: salary, savings/checking,
  stocks, 401(k), IRA, 529, real estate, mortgage, debt, and expenses
- Money flows as fixed amounts, percentages, or "whatever remains", monthly/quarterly/annually,
  with priorities and conditions (e.g. only when a balance is over $10k)
- Start/end dates on any node (a loan that ends, childcare that stops)
- Step through the simulation month by month, and pause to make manual moves (sell stocks,
  pay off a debt, transfer money), then continue
- Federal and state tax estimates
- Save/load graphs as JSON; an example graph loads and runs when you open the app

## Quickstart

You need **Python 3.10+** and **Node.js 18+**.

**1. Backend** (FastAPI on port 5000):

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 5000
```

Interactive API docs: http://localhost:5000/docs

**2. Frontend** (React on port 3000), in a second terminal from the repo root:

```bash
npm install   # uses package-lock.json
npm start
```

Open http://localhost:3000. The example graph loads and simulates automatically.
Use **File → New Graph** to start from scratch, or **File → Load Example** to get it back.

### Configuration

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `REACT_APP_API_URL` | frontend | `http://localhost:5000` | Backend URL |
| `DOUGHFLOW_CORS_ORIGINS` | backend | `http://localhost:3000` | Comma-separated origins allowed to call the API |

## How it works

```
Salary ──► Checking ──► Savings ──► Brokerage
              │
              ├──► Mortgage
              └──► Student loan
```

- **Nodes** are financial modules (`backend/modules/`). Each one implements `BaseModule`:
  it keeps its own state and processes one month at a time (interest, growth, amortization…).
- **Edges** move money between nodes each month, in priority order.
- **The engine** (`backend/engine/graph_executor.py`) runs nodes in dependency order,
  resolves cycles by iterating to convergence, and records a snapshot per month.
- **The frontend** (`src/`) is a React Flow editor plus panels for running the simulation,
  stepping through months, and making transactions.

Where it's headed: [docs/ROADMAP.md](docs/ROADMAP.md) (what-if scenarios, events, goals, uncertainty).

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full tour: module interface,
API endpoints, state management, and known pitfalls.

## Project layout

```
backend/
  app.py            FastAPI app and routes
  schemas.py        Request models
  engine/           Simulation engine, cycle detection, transactions, ledger
  modules/          One file per financial building block
  tax/              Federal/state tax and deduction calculators
  tests/            pytest suite
src/
  components/       Flow canvas, nodes, forms, panels
  context/          Graph state (React context + reducer)
  hooks/            API calls, save/load
  examples/         The example graph
docs/               Architecture notes
```

## Running tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## Known issues

The simulation engine has bugs that affect the numbers. The big ones:

- Money moved between accounts can be double-counted, which inflates net worth
- Graphs with cycles can apply a month's interest and flows more than once
- Net worth doesn't include property equity
- Taxes are estimated separately and aren't deducted inside the simulation

These are tracked in [GitHub issues](https://github.com/abzgupta/doughflow.io/issues), and
fixing them is the most valuable contribution right now.

## Contributing

Bug reports, fixes, and new modules are all welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Disclaimer

**DoughFlow is an educational tool. It is not financial, investment, tax, or legal advice.**

- The simulations are simplified models built on hypothetical assumptions. They may contain
  errors (see [Known issues](#known-issues)) and will not match real-world outcomes.
- Tax calculations are rough estimates. Tax rules are simplified and may be out of date or
  wrong for your situation.
- Before making any financial decision, consult a qualified **financial advisor**, a
  **tax advisor or CPA**, and where relevant an **attorney**, who can account for your
  specific circumstances.
- You use DoughFlow entirely at your own risk. You are solely responsible for any decisions
  you make. The authors and contributors accept no liability for any financial loss or other
  damages arising from use of the software or reliance on its output. See also the
  warranty disclaimer and limitation of liability in the [MIT License](LICENSE).

## License

[MIT](LICENSE)
