# CamJam Frontend Build & Test Guide

This guide explains how to set up, build, and test the CamJam control console UI located in the `frontend/` workspace.

## Prerequisites
- Node.js 20+
- npm 10+

## Installation
```bash
cd frontend
npm install
```
> **Note:** Some corporate or offline environments may block scoped package downloads (e.g., `@radix-ui/react-slider`). If installation fails, mirror these packages to an accessible registry or vendor them locally.

## Development Server
```bash
npm run dev
```
This starts a Vite development server. The console connects to the control service via `VITE_CONTROL_WS` (defaults to `ws://localhost:8080/ws`).

## Production Build
```bash
npm run build
```
The command runs TypeScript type-checking and produces optimized assets in `dist/`.

## Testing
```bash
npm test
```
The Vitest suite exercises drive command issuance, telemetry rendering, accessibility rules, and responsive layout logic. Use `npm run test:watch` during iterative development.

## Linting & Formatting
Tailwind CSS utility classes and component structure follow the design tokens described in `styling-guide.md`. Integrate ESLint/Prettier as needed (not bundled yet) to enforce conventions.

## Environment Variables
| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_CONTROL_WS` | `ws://localhost:8080/ws` | WebSocket endpoint for drive, PanTilt, and telemetry channels. |
| `VITE_ANALYTICS_KEY` | (unset) | Optional instrumentation key for analytics forwarding. |

Set variables in a `.env.local` file to avoid checking secrets into version control.
