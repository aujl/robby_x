# CamJam Maintenance Runbook

This runbook describes the recurring operational procedures that keep the
CamJam platform reliable. Perform the quick checks before each mission and the
full service at least once per quarter.

## Servo Recalibration

1. **Trigger the calibration mode** by running
   `sudo /opt/camjam/bin/control --calibrate-servos` or the provisioning script
   with `--calibrate` if the binary is unavailable.
2. **Verify neutral positions**: the pan and tilt arms should rest at 90°.
   Adjust the horn couplers if the range is off by more than ±2°.
3. **Persist offsets**: confirm `/var/lib/camjam/servos.yaml` updates with the
   latest offsets. Commit the file to configuration management if you are using
   GitOps for fleet state.
4. **Functional test**: run the head sweep diagnostic (`sudo systemctl start
   camjam-diagnostics.service`) and ensure smooth motion without chatter.

## Camera Focus Maintenance

1. Remove the acrylic dome and inspect the lens for dust or fingerprints.
2. With the camera service stopped, attach an HDMI display and run
   `libcamera-hello --autofocus-mode=continuous`.
3. Use the manual focus ring to achieve a sharp image at 1.5 m. Tighten the lens
   lock screw to hold the setting.
4. Restart the camera streaming unit and verify the feed through the fleet
   dashboard. Update `/etc/camjam/camera.yaml` if the focal distance changed.

## Battery Health Checks

1. Inspect all wiring for fraying or pinched insulation. Replace suspect leads
   immediately.
2. Measure pack voltage under load. Replace cells if the loaded voltage drops
   below 1.1 V per cell or if capacity declines more than 20% from baseline.
3. Log cycle counts in the fleet maintenance tracker. Rotate packs to balance
   usage across the fleet.
4. Dispose of exhausted NiMH cells following local recycling regulations.

## TLS Certificate Renewal

1. The CamJam control API uses TLS certificates stored in
   `/etc/camjam/tls/{fullchain.pem,privkey.pem}`. Certificates are issued via
   an ACME DNS-01 workflow.
2. The provisioning process installs a timer unit, `camjam-tls-renew.timer`, that
   runs weekly. Confirm it is active using `systemctl list-timers`.
3. When a renewal occurs, the post-hook reloads `camjam-control.service`. Verify
   the control API responds with the new expiry timestamp via
   `curl https://camjam-<id>.local:8443/healthz`.
4. If automatic renewal fails, run the manual fallback:
   ```bash
   sudo certbot certonly \
     --manual --preferred-challenges dns \
     -d camjam-<id>.local
   sudo systemctl reload camjam-control.service
   ```
5. Document any manual intervention in the operational logbook and raise an
   incident if the outage exceeds 15 minutes.
