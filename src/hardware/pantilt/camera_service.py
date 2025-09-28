"""PanTilt camera streaming service built on top of Picamera2/libcamera."""

from __future__ import annotations

import importlib
import io
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ServoCommand:
    pan: float
    tilt: float


class ServoControllerProtocol(Protocol):  # pragma: no cover - structural typing aid
    def move_to(self, pan: float, tilt: float) -> None: ...


class StreamError(RuntimeError):
    """Raised when the video pipeline fails to start."""


class PanTiltCameraService:
    """Coordinate Picamera2 streaming with PanTilt servo alignment."""

    def __init__(
        self,
        *,
        servos: ServoControllerProtocol | None = None,
        resolution: tuple[int, int] = (1280, 720),
        framerate: int = 30,
        pan_offset: float = 0.0,
        tilt_offset: float = 0.0,
        camera_factory: Callable[[], Any] | None = None,
        encoder_factory: Callable[[], Any] | None = None,
        output_factory: Callable[[Any], Any] | None = None,
        still_image_provider: Callable[[], bytes] | None = None,
    ) -> None:
        self._servos = servos
        self._resolution = resolution
        self._framerate = framerate
        self._pan_offset = pan_offset
        self._tilt_offset = tilt_offset
        self._still_image_provider = still_image_provider
        self._lock = threading.Lock()
        self._last_command = ServoCommand(0.0, 0.0)
        self._camera = None
        self._active_output = None
        self._is_streaming = False
        self._last_error: Exception | None = None
        self._fallback_frame: bytes | None = None

        picamera2_module = importlib.import_module("picamera2")
        outputs_module = importlib.import_module("picamera2.outputs")

        picamera_cls = picamera2_module.Picamera2
        mjpeg_encoder_cls = getattr(picamera2_module, "MjpegEncoder", None)
        if mjpeg_encoder_cls is None:
            mjpeg_encoder_cls = getattr(picamera2_module, "MJPEGEncoder")
        file_output_cls = outputs_module.FileOutput

        self._camera_factory = camera_factory or picamera_cls
        self._encoder_factory = encoder_factory or (lambda: mjpeg_encoder_cls())
        self._output_factory = output_factory or (lambda destination: file_output_cls(destination))

    @property
    def is_streaming(self) -> bool:
        """Return whether the camera is actively streaming video."""
        return self._is_streaming

    @property
    def last_error(self) -> Exception | None:
        """Return the last streaming error encountered, if any."""
        return self._last_error

    def command_servos(self, pan: float, tilt: float) -> None:
        """Command the servos to the requested angles with alignment offsets applied."""
        with self._lock:
            self._last_command = ServoCommand(pan, tilt)
            self._apply_servo_alignment()

    def start_stream(self, destination: Any) -> None:
        """Begin streaming video to the provided destination sink."""
        with self._lock:
            if self._is_streaming:
                return

            camera = self._camera_factory()
            frame_duration = int(1_000_000 // max(self._framerate, 1))
            config = camera.create_video_configuration(
                main={"size": self._resolution, "format": "RGB888"},
                controls={"FrameDurationLimits": (frame_duration, frame_duration)},
            )
            config.setdefault("controls", {})["FrameDurationLimits"] = (
                frame_duration,
                frame_duration,
            )
            camera.configure(config)

            encoder = self._encoder_factory()
            output = self._output_factory(destination)

            try:
                camera.start_recording(encoder, output)
            except Exception as exc:  # pragma: no cover - exercised via tests
                camera.close()
                if hasattr(output, "close"):
                    try:
                        output.close()
                    except Exception:
                        pass
                self._camera = None
                self._last_error = exc
                self._is_streaming = False
                self._fallback_frame = self._resolve_fallback_frame()
                raise StreamError("Failed to start PanTilt video stream") from exc

            self._camera = camera
            self._active_output = output
            self._is_streaming = True
            self._last_error = None
            self._fallback_frame = None
            self._apply_servo_alignment()

    def stop_stream(self) -> None:
        """Stop any active video stream and release camera resources."""
        with self._lock:
            camera = self._camera
            if not camera:
                return

            try:
                camera.stop_recording()
            finally:
                camera.close()
                self._is_streaming = False
                self._camera = None
                output = self._active_output
                self._active_output = None
                if output and hasattr(output, "close"):
                    try:
                        output.close()
                    except Exception:
                        pass

    def get_frame(self) -> bytes:
        """Capture a JPEG frame from the stream or return a cached fallback image."""
        with self._lock:
            if self._is_streaming and self._camera:
                buffer = io.BytesIO()
                try:
                    self._camera.capture_file(buffer, format="jpeg")
                except Exception:
                    return self._resolve_fallback_frame()
                return buffer.getvalue()
            return self._resolve_fallback_frame()

    def _apply_servo_alignment(self) -> None:
        if not self._servos:
            return
        aligned_pan = self._last_command.pan + self._pan_offset
        aligned_tilt = self._last_command.tilt + self._tilt_offset
        self._servos.move_to(aligned_pan, aligned_tilt)

    def _resolve_fallback_frame(self) -> bytes:
        if self._fallback_frame is not None:
            return self._fallback_frame
        if self._still_image_provider is not None:
            frame = self._still_image_provider()
            self._fallback_frame = frame
            return frame
        return self._capture_still_from_camera()

    def _capture_still_from_camera(self) -> bytes:
        camera = self._camera
        if camera is None:
            camera = self._camera_factory()
            try:
                if hasattr(camera, "create_still_configuration"):
                    config = camera.create_still_configuration(main={"size": self._resolution})
                else:
                    config = camera.create_video_configuration(main={"size": self._resolution})
                camera.configure(config)
                buffer = io.BytesIO()
                camera.capture_file(buffer, format="jpeg")
                return buffer.getvalue()
            finally:
                camera.close()
        buffer = io.BytesIO()
        camera.capture_file(buffer, format="jpeg")
        frame = buffer.getvalue()
        self._fallback_frame = frame
        return frame


__all__ = ["PanTiltCameraService", "StreamError"]
