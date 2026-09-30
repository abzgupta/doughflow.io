# DoughFlow Vision & Roadmap

**One-line pitch:** *Model your whole financial life in one place, change anything, and see what happens.*

Money gets planned in two disconnected halves:
- **Personal finance tools** (budgets, emergency-fund calculators, mortgage calculators) treat income and markets as fixed.
- **Investing tools** (portfolio trackers, retirement calculators) treat markets in isolation and assume your paycheck, bills and big life decisions never change.

In real life they're one system. A new baby changes how much you can invest. A market drop changes whether you can afford the house. A raise changes whether paying off the mortgage beats investing. DoughFlow connects the halves: income, spending, savings, debt, investments and property in **one model**, so any change ripples through everything else.

**What-if scenario planning** is the product. You keep a base plan and create variations of it, then compare the outcomes side by side. Scenarios come in three kinds:
- **Decisions you're weighing:** buy vs. rent, buy a rental property, pay down debt vs. invest, max the 401(k) vs. a brokerage account, retire at 55 vs. 60, take the lower-paying job you'd enjoy.
- **Life changes you expect:** a baby, childcare ending, college costs, a move, a raise or career change, caring for a parent.
- **Shocks you can't control:** a market crash or boom, a job loss, rate hikes, inflation, a big medical bill. These double as stress tests: "does my plan survive this?"

Every scenario answers the same questions:
- **Where do I end up?** Net worth, liquid cash and debt over time, compared with the base plan.
- **Can I afford it?** Does cash ever run short, and if so, when, and what gets sold or borrowed to cover it (and at what cost in taxes, penalties and losses)?
- **Does it reach my goals?** A house down payment by 2029, college funded, retirement at 60.
- **What's the trade-off?** How much better or worse each choice is, and in which years.

The graph editor is the engine room. The product is answering "what happens if…?" for any change.

## Where the app is today

Already there, and it's a solid foundation:
- A whole-picture model with 10 module types connecting income, accounts, investments, property and debt (`backend/modules/`)
- A month-by-month engine with priority-ordered money flows (`backend/engine/graph_executor.py`)
- Start/end dates on any node (`BaseModule.is_active_for_date`), so time-bound things like a car loan, daycare or a salary can already be expressed
- Mid-simulation actions (sell stocks, pay debt, transfer) in `engine/transactions.py`
- Federal/state tax calculators (`backend/tax/`), not yet wired into the simulation

## Gaps

**1. The numbers can't be trusted yet (blocks everything).**
- Transfers create money ([#4](https://github.com/abzgupta/doughflow.io/issues/4)), properties resell every month ([#5](https://github.com/abzgupta/doughflow.io/issues/5)), unconnected nodes are skipped ([#6](https://github.com/abzgupta/doughflow.io/issues/6)), cycles double-apply ([#8](https://github.com/abzgupta/doughflow.io/issues/8)), and step/continue crash ([#10](https://github.com/abzgupta/doughflow.io/issues/10)).
- Comparing scenarios on a broken ledger compares noise.

**2. No scenario layer (the core missing piece).**
- There's one graph. You can't keep a base plan plus named variants that change a few things, run them together, and compare them.
- Today the only way to try a what-if is to edit your plan and lose the original.

**3. No way to express changes over time.**
- A what-if is mostly "from month X, something changes": a new expense, a raise, a purchase, a market move, an income stopping or starting.
- Today that means hand-editing node configs and dates. There's no first-class event (one-time or recurring, starting at a date) that a scenario can apply to the base plan, and no library of common ones.

**4. Markets are a constant.**
- Stocks grow at a fixed `expected_annual_return`. `monthly_volatility` exists in the schema but is never used (`modules/stock_portfolio.py`).
- You can't say "a 30% drop in 2027 with a 3-year recovery", replay history (2000–02, 2008, 2020), or see a range of outcomes instead of one line.
- Inflation and interest rates are per-node percentages, not shared assumptions a scenario can change in one place.

**5. Running short of money isn't modeled.**
- A fixed bill pays `min(amount, available)` (`graph_executor.py:216`). When cash is short, the unpaid part silently disappears.
- There's no shortfall tracking and no automatic "cover it from the next account" (savings → brokerage → credit → retirement, with the right taxes and penalties).
- That makes "can I afford this?" and every stress test unanswerable.

**6. Taxes aren't in the flow (#9).**
- Many decisions are really tax decisions: Roth vs. traditional, selling appreciated stock, rental depreciation, the mortgage interest deduction. The simulation ignores taxes entirely.

**7. No goals.**
- There's nothing to aim at ("$80k down payment by 2029", "retire at 60 with $2M"), so the app can't say whether a scenario reaches the goal or misses it.

**8. The output doesn't answer the question.**
- The UI shows per-account balances month by month.
- It needs headline comparisons ("Buying the rental: +$140k net worth by 2036, but cash dips below $5k in 2027") and a chart of the scenarios on shared axes.

**9. Hard to get started.**
- Building a realistic graph by wiring nodes takes a lot of knowledge. A short guided setup that generates the base graph would open the app to far more people.

## Roadmap

**Phase 1: Trustworthy ledger** (issues #4–#10)
- Make module state the single source of truth for balances.
- Include isolated nodes, fix real estate, and fix cycle iteration.
- Add a conservation test: net-worth change = income − spending ± market moves.

**Phase 2: Scenarios and events (the core)**
- **Scenario:** a named set of changes applied to the base graph, stored with it in the saved JSON.
- **Changes:** override a node's config, add or remove a node or edge, or apply an event.
- **Events:** typed and dated, one-time or recurring, e.g.:
  - `income_change` (raise, job loss, new job)
  - `expense_change` (baby, childcare, a move)
  - `purchase` (house, car, rental)
  - `market_change` (a return shift or drawdown with a recovery curve)
  - `rate_change`
  - `windfall`
- **API:** `POST /api/scenarios/compare` runs the base plus N scenarios and returns series and summary metrics for each.
- **Shared assumptions:** inflation, market return and interest rates, which any scenario can override.

**Phase 3: Affordability and outcomes**
- Record shortfalls, and add a configurable withdrawal order with penalties and taxes.
- Metrics per scenario: net worth at the end and at checkpoints, lowest liquid cash, first shortfall month (runway), forced sales and their cost, taxes paid, and goal hit or miss.
- Wire taxes into the monthly flow (#9).

**Phase 4: Uncertainty**
- Use volatility, or historical return sequences, to run a Monte Carlo of a few hundred paths.
- Report ranges and probabilities ("82% chance you reach the goal", "5% chance of a cash shortfall") instead of one line.

**Phase 5: Experience**
- A Scenarios panel: duplicate the base, apply changes or pick from a library, and compare on one chart with a plain-language summary of the differences.
- Guided setup that creates the base graph.
- Keep the graph editor as the advanced view.

## Next milestone
Phase 1, then a thin slice of Phase 2 that proves the whole idea end to end:
- Fix #4, #6 and #10.
- Add scenarios as config overrides plus three event types: `income_change`, `expense_change` and `market_change`.
- Add the compare endpoint with a handful of metrics: final net worth, lowest liquid cash, first shortfall month.
- Add a simple UI to create two or three scenarios from the example graph and see them on one chart.

Demo it with a mix of kinds, so no single use case dominates: **"Have a baby in 2027"**, **"Buy the rental in 2028"**, and **"Market drops 30% in 2027"**, each compared against the base plan.

## Definition of done for that milestone
- **Unit tests:**
  - Transfer conservation.
  - Each event type changes the right node from the right month.
  - A scenario leaves the base graph untouched.
- **API test:** `/api/scenarios/compare` on `src/examples/sampleGraph.json` with three scenarios. Check the directions: the baby scenario has lower net worth than base, the crash has lower portfolio value in the shock month, and the base run is unchanged.
- **Manual:** in the browser, create the three example scenarios, compare the chart against a rough hand calculation, and confirm the summary text matches the numbers.
