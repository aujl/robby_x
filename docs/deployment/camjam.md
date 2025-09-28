# CamJam Deployment Guide

This guide captures the platform requirements and deployment workflow for
CamJam robots. It assumes you are provisioning a Raspberry Pi 4B with the
official PanTilt HAT and CamJam EduKit robotics chassis.

## Raspberry Pi OS Preparation

1. **Flash Raspberry Pi OS Lite (64-bit)** onto a microSD card using Raspberry Pi
   Imager. Enable SSH and set the hostname to `camjam-<id>` for fleet
   traceability.
2. **First boot configuration**:
   - Attach the Pi to a wired network and power it using a bench supply or the
     CamJam battery pack.
   - Run `sudo raspi-config` to expand the filesystem, set the locale/timezone,
     enable I2C, SPI, and the camera interface, and configure passwordless sudo
     for the `pi` operator account.
   - Update the base image: `sudo apt-get update && sudo apt-get -y dist-upgrade`
     followed by a reboot.
3. **Filesystem layout**: create `/opt/camjam` for application code and
   `/var/lib/camjam` for persistent state (telemetry buffers, calibration files,
   and provisioning lock files).

## PanTilt HAT Servo Calibration

1. Verify the HAT is seated and that the servos are connected (pan to channel 0,
   tilt to channel 1).
2. Run the provisioning script (`deploy/camjam/provision_camjam.sh --calibrate`)
   which will install dependencies and launch the servo calibration routine.
3. During calibration, use the on-screen prompts to centre each axis, then store
   the offsets. The offsets are written to `/var/lib/camjam/servos.yaml` and
   applied on boot by the control service.
4. If mechanical limits are encountered, loosen the servo horn screws, re-seat
   the servos in their neutral positions, and repeat the calibration routine.

## pigpiod and libcamera Services

1. Ensure `pigpiod` is enabled for low-latency PWM output. The provisioning
   script installs the package and creates a systemd override with the flags
   `-x` (disable socket interface) and `-t 0` (highest priority).
2. Install the `libcamera-apps` suite. The camera streaming unit wraps
   `libcamera-vid` to publish an H.264 stream on TCP port 8554.
3. After provisioning, confirm service status:
   ```bash
   sudo systemctl status pigpiod.service
   sudo systemctl status camjam-camera.service
   sudo systemctl status camjam-control.service
   ```
4. If the camera service fails to start, run `libcamera-hello` manually to check
   sensor detection and re-seat the camera ribbon cable as required.

## Battery Safety

1. Use only the CamJam recommended 4xAA NiMH packs or a regulated 5V/3A supply.
2. Inspect the pack before each deployment for swelling, corrosion, or damaged
   leads. Replace any compromised cells immediately.
3. Monitor voltage during operation. The diagnostics service halts the robot and
   triggers an audible alert when pack voltage drops below 4.6V.
4. Never charge NiMH cells while installed in the robot. Remove the pack and use
   a smart charger with delta-V detection.
5. Store batteries at room temperature with a 40–60% state of charge. Rotate
   packs quarterly to prevent capacity loss.
