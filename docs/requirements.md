# Requirements

## Overview
The project builds on the [Build a Buggy tutorial](https://projects.raspberrypi.org/en/projects/build-a-buggy/3), adapting the hardware platform for a locally networked, camera-enabled teleoperation experience. Requirements are captured as user stories describing desired behavior, latency expectations, safety tolerances, and video-streaming capabilities.

## User Stories

### Local-network Driving
- As a **driver**, I want to connect to the buggy over a secure local network so that I can avoid exposing the robot to the public internet.
- As a **driver**, I want the control UI to auto-discover or easily configure the buggy's IP address so that I can start a session with minimal setup.
- As a **driver**, I want real-time feedback on connection quality so that I can react before controls become unresponsive.
- As an **operator**, I want the system to continue functioning if the network temporarily drops for up to 2 seconds so that momentary Wi-Fi glitches do not end a session.

### Latency Tolerances
- As a **driver**, I want motion commands to reach the buggy with a command latency under 100 ms on a stable Wi-Fi network so that maneuvering feels responsive.
- As a **driver**, I want on-screen status indicators when latency exceeds 150 ms so that I can reduce speed or pause driving.
- As a **tester**, I want automated latency measurements logged during every session so that we can verify performance against the 100 ms target.

### Safety Limits
- As a **safety officer**, I want configurable maximum speed and turn rate limits so that the buggy never exceeds safe motion parameters indoors.
- As a **driver**, I want an emergency stop (E-stop) button in the UI and on the hardware that immediately cuts motor power so that I can respond to hazards.
- As a **maintainer**, I want the system to require periodic heartbeats from the controller (every 250 ms) so that motors stop if communication is lost for more than 500 ms.
- As a **system administrator**, I want audit logs of E-stop events and limit changes so that I can analyze safety incidents.

### PiCam Streaming
- As a **driver**, I want a low-latency PiCam video stream embedded next to the control UI so that I can see obstacles while driving remotely.
- As a **driver**, I want adaptive video quality that prioritizes frame rate (minimum 20 FPS) when bandwidth is limited so that motion remains visible.
- As a **viewer**, I want the ability to pop out the stream to full screen so that multiple team members can observe.
- As a **developer**, I want the video streaming pipeline to expose diagnostics (bitrate, dropped frames, end-to-end latency) so that I can tune encoder settings.

## Non-functional Requirements
- The system SHALL run on Raspberry Pi OS with minimal additional software dependencies, keeping install time under 10 minutes.
- All services SHALL start via `systemd` or Docker Compose to simplify deployment and recovery.
- The project SHALL provide automated tests for control logic and network services with a target coverage of 80%.
- Documentation SHALL be updated whenever requirements or interfaces change to keep operators aligned.
