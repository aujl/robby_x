# Development Guidelines

## Coding Standards

### Python (Backend Services)
- Follow [PEP 8](https://peps.python.org/pep-0008/) with `black` enforcing a 100-character line length (see `pyproject.toml`).
- Use type hints everywhere and enable `mypy` in strict mode for core packages. Treat warnings as errors locally and in CI.
- Structure services with explicit dependency injection (FastAPI `Depends`) to isolate hardware adapters, safety logic, and persistence layers.
- Wrap GPIO and camera interactions in adapter classes that expose async-friendly interfaces; never block the event loop with long-running I/O.
- Log with `structlog` using JSON format to feed analytics pipelines.
- Guard all safety-critical functions (e.g., motor commands) with rate limiting and input validation to enforce speed/turn bounds.

### TypeScript/React (Frontend)
- Use functional components with hooks; avoid class components.
- Enforce ESLint (see `.eslintrc.cjs` for CamJam rules) and Prettier formatting.
- Centralize shared types in `/src/types`; align them with backend Pydantic models via generated OpenAPI typings.
- Keep state management modular: use React Query for server state and Zustand for UI-local state.
- Implement accessibility best practices (ARIA roles, keyboard navigation) in the control surface.
- Store theme constants and layout breakpoints in `/src/styles/tokens.ts` to support responsive design.

### Infrastructure & Configuration
- Store configuration in environment variables processed through `pydantic-settings`; commit sample `.env.example` files, never secrets.
- Manage `systemd` unit files and Docker Compose manifests under `deploy/` with consistent naming.
- Document every new service contract via OpenAPI or AsyncAPI in `docs/api/` (future scope).

## Test-Driven Development Workflow
1. **Specify Requirements:** Capture new capabilities as user stories or acceptance criteria in `docs/requirements.md` or linked issue trackers. Include latency, safety, and telemetry considerations.
2. **Design Tests First:**
   - Backend: write failing unit tests with `pytest` + `pytest-asyncio` and integration tests that simulate GPIO and camera adapters using fakes.
   - Frontend: create failing tests with Vitest and React Testing Library covering UI interactions, latency indicators, and accessibility.
   - Streaming: script GStreamer/Janus test harnesses to validate video latency and resilience before implementation.
3. **Implement Iteratively:** Develop the minimal code to satisfy the tests, preferring small, reviewable commits. Use feature flags for experimental drivers or codecs.
4. **Run the Test Suite:** Execute `pytest -m "camjam_unit or camjam_mocked_hw"`, `pytest -m camjam_simulation`, and `npm run test:coverage --prefix frontend` locally before pushing. Aim for &gt;85% Python coverage (enforced via `pyproject.toml`) and track Vitest coverage trends in CI.
5. **Refactor with Confidence:** After tests pass, refactor for readability and maintainability. Update diagrams and documentation if interfaces change.
6. **Review & Definition of Done:** Ensure linting passes, update changelogs, and confirm that monitoring dashboards capture new metrics. A story is complete only when documentation, diagrams, and test evidence accompany the change.

## Continuous Integration Expectations
- GitHub Actions workflows (`ci.yml`) lint, type-check, and run CamJam simulator/unit/mocked hardware suites on every PR while publishing combined coverage reports as artifacts.
- Hardware-in-the-loop smoke tests run nightly using a staging buggy (`hil-nightly.yml`); failures block releases.
- Performance benchmarks capture command latency, video end-to-end latency, and dropped frame counts; regressions over 10% trigger alerts.
- Security scans (`pip-audit`, `npm audit`, and container scanning) must pass before merging.
