# Contributing to DoughFlow

Thanks for your interest! DoughFlow is a small project, so the process is light.

## Getting set up

Follow the [Quickstart](README.md#quickstart) to run the backend and frontend locally,
then install the test dependencies:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) before diving in, especially the
**Frontend Pitfalls** section if you're touching `GraphContext` or `SimulationPanel`.

## Where to help

- **Engine correctness**: the [open issues](https://github.com/abzgupta/doughflow.io/issues)
  list known bugs in the simulation math. A fix plus a test that proves it is the most
  valuable thing you can send.
- **New modules**: HSA, pension, Social Security, car purchase…
- **UI/UX**: the interface needs a lot of love.

## Making a change

1. Fork the repo and create a branch from `main`.
2. Make your change. Keep pull requests focused on one thing.
3. Add or update tests in `backend/tests/` for backend changes.
4. Check that `pytest` passes and `npm run build` succeeds.
5. Open a pull request describing what changed and why.

## Adding a module type

1. Create `backend/modules/your_module.py` with a class that inherits from `BaseModule`
   (see `backend/modules/base_module.py`) and implements `module_type`, `flow_direction`,
   `get_config_schema`, `initialize`, and `process_month`.
2. Export it from `backend/modules/__init__.py`.
3. Register it in `get_module_registry()` and `create_module_from_type()` in `backend/app.py`.
4. Add it to the frontend: the node palette in `src/components/flow/FlowToolbar.js`, plus
   its look and config form in `src/components/nodes/BaseNode.js`,
   `src/components/forms/NodeConfigDrawer.js`, and `src/components/flow/FlowCanvas.js`
   (search for an existing type like `real_estate` to see each spot).
5. Add a test in `backend/tests/`.

## Adding a transaction type

1. Add a handler in `backend/engine/transactions.py`.
2. Add a case in the `/api/transaction` endpoint in `backend/app.py`.
3. Add the UI in `src/components/panels/TransactionModal.js`.

## Reporting bugs

Open an issue with the steps to reproduce. If it's a simulation bug, attach the graph
(**File → Save Graph**) and say which numbers look wrong and what you expected.
