# robby_x

[![CI](https://github.com/aujl/robby_x/actions/workflows/ci.yml/badge.svg)](https://github.com/aujl/robby_x/actions/workflows/ci.yml)
[![CamJam HIL](https://github.com/aujl/robby_x/actions/workflows/hil-nightly.yml/badge.svg)](https://github.com/aujl/robby_x/actions/workflows/hil-nightly.yml)
[![Coverage](https://img.shields.io/badge/coverage-camjam%20suite-blue)](docs/testing/camjam-strategy.md)

RasPi robot control stack for the CamJam buggy, PanTilt camera rig, and telemetry front-end.

## Development quickstart

1. Install tooling: `pip install -e .[dev,sim]` and `npm install --prefix frontend`.
2. Install git hooks: `pre-commit install` to run CamJam-specific linting, typing, simulator smoke tests, and frontend formatting/linting before each commit.
3. Run the focused test suites:
   - `pytest -m "camjam_unit or camjam_mocked_hw"`
   - `pytest -m camjam_simulation`
   - `npm run test:coverage --prefix frontend`

See [`docs/testing/camjam-strategy.md`](docs/testing/camjam-strategy.md) for the full unit/integration/HIL validation matrix.
