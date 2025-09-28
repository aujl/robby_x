# PanTilt Streaming Strategy

## Protocol selection

We rely on the Picamera2 `libcamera` stack and stream encoded MJPEG over HTTP. MJPEG keeps the server implementation simple (a byte stream over an HTTP response) and pairs cleanly with `start_recording(MjpegEncoder, FileOutput)` from Picamera2. WebRTC was considered for its adaptive bitrate and built-in NAT traversal, but it introduces extra signaling dependencies and higher CPU usage on the rover. The rover already operates on a constrained single-board computer, so the deterministic latency and low memory footprint of a libcamera-powered MJPEG stream outweigh the benefits of WebRTC for this release. The service still exposes hooks for swapping encoders if a future upgrade to WebRTC or H.264 becomes necessary.

## Latency targets

The PanTilt video path must keep motion-to-photon latency under **220 ms** during teleoperation. This budget matches the operator’s muscle memory for servo control and assumes:

- Picamera2 pipeline produces 30 fps frames (≈33 ms per frame).
- Encoder and HTTP buffering contribute less than 60 ms.
- Network traversal on the local Wi-Fi stays below 100 ms.
- The frontend applies minimal rebuffering (<20 ms) by avoiding extra HTML5 video pipelines and rendering the MJPEG stream directly in an `<img>` tag.

If latency spikes above 220 ms for three consecutive frames, the UI will surface a warning badge and offer a still-image fallback while the service attempts to recover the stream.

## Servo coordination

The `PanTiltCameraService` keeps camera and servo motion aligned by:

1. Tracking the most recent logical pan/tilt command issued by the control subsystem.
2. Applying calibrated offsets (accounting for camera mounting skew) before dispatching the command to the physical servos.
3. Replaying the compensated command whenever the camera pipeline restarts so that the optics and servos remain synchronized after transient faults.

This coordination ensures that the operator sees an accurate representation of the servo aim and that presets (center, sweep, inspect) line up with the real camera axis.

## Fallback still-image mode

When the live stream fails to start or drops unexpectedly, the service captures or serves a cached JPEG still. The frontend swaps to that image while allowing the operator to retry the stream without losing situational awareness.
