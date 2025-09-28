# ADR 0001: Tech Stack Selection

- Status: Accepted
- Date: 2024-09-28

## Context
The teleoperated buggy extends the Raspberry Pi "Build a Buggy" project with network control, safety interlocks, and PiCam streaming. The stack must run reliably on Raspberry Pi OS, support low-latency bidirectional messaging, integrate with WebRTC for video, and remain maintainable by a small cross-functional team. Hardware interfaces (GPIO, I2C, CSI) need deterministic handling, while the UI must deliver responsive controls on desktops and mobile browsers.

## Decision
- **Backend Framework:** Adopt **FastAPI (Python)** running under Uvicorn. FastAPI offers async I/O for WebSocket control channels, rich validation via Pydantic, and a small footprint on Raspberry Pi hardware. Python already aligns with Raspberry Pi tooling and hardware-access libraries (e.g., `gpiozero`, `picamera2`).
- **Frontend Stack:** Use a **React + TypeScript** single-page application bootstrapped with Vite. React components provide modular UI composition for the control surface, telemetry dashboards, and video overlays. TypeScript enforces type safety when integrating with the WebSocket and WebRTC APIs.
- **Messaging Strategy:** Employ a **WebSocket gateway** for command and telemetry exchange supplemented by **MQTT** internally between services. WebSockets give the browser a persistent bidirectional channel with minimal overhead. MQTT topics allow decoupled microservices (safety manager, telemetry logger, analytics pipeline) to exchange messages with QoS controls and retained states.
- **Video Transport:** Use **WebRTC** for the PiCam stream with `gstreamer` producing H.264 frames and the backend handling signaling over HTTPS/WebSockets. WebRTC minimizes latency and adapts to variable Wi-Fi conditions.
- **Persistence:** Store session metrics, safety events, and telemetry in **TimescaleDB (PostgreSQL extension)**. TimescaleDB provides time-series compression, continuous aggregates for latency analysis, and runs comfortably on a Pi or remote server. Short-term buffering uses Redis for transient state and rate limiting.

## Consequences
- FastAPI requires disciplined async code and structured dependency injection but yields excellent documentation via OpenAPI.
- React + TypeScript increases the build tooling complexity; however, it delivers a component model suitable for rapid UI iteration and reuse.
- Combining WebSockets and MQTT introduces operational overhead (broker configuration), yet it separates external-facing protocols from internal service choreography, aiding scalability.
- WebRTC's learning curve is non-trivial; investment is needed to maintain ICE/TURN configuration, but the latency benefits align with the 100 ms control target and 20+ FPS video goals.
- TimescaleDB adds a database dependency beyond SQLite, but it unlocks advanced analytics on latency and safety events, supporting the project's quantitative evaluation objectives.
