from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from typing import Generator
from unittest.mock import MagicMock, call

import pytest


@pytest.fixture(autouse=True)
def picamera2_stubs(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    class DummyEncoder:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class DummyFileOutput:
        def __init__(self, destination: object) -> None:
            self.destination = destination
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class DummyCamera:
        def __init__(self) -> None:
            self.configured = None
            self.recording = False
            self.closed = False
            self.stopped = False
            self._captured_frames = []

        def create_video_configuration(self, **kwargs):
            self.last_configuration_request = kwargs
            return {"main": kwargs.get("main", {}), "controls": kwargs.get("controls", {})}

        def configure(self, config):
            self.configured = config

        def start_recording(self, encoder, output):
            self.recording = True
            self.encoder = encoder
            self.output = output

        def stop_recording(self):
            self.recording = False
            self.stopped = True

        def capture_file(self, fileobj, format="jpeg"):
            frame = b"live-frame"
            self._captured_frames.append(frame)
            fileobj.write(frame)

        def close(self):
            self.closed = True

    module = SimpleNamespace(Picamera2=DummyCamera, MjpegEncoder=DummyEncoder)
    outputs_module = SimpleNamespace(FileOutput=lambda destination: DummyFileOutput(destination))
    monkeypatch.setitem(sys.modules, "picamera2", module)
    monkeypatch.setitem(sys.modules, "picamera2.outputs", outputs_module)
    yield
    monkeypatch.delitem(sys.modules, "picamera2", raising=False)
    monkeypatch.delitem(sys.modules, "picamera2.outputs", raising=False)
    importlib.invalidate_caches()


def import_service():
    import src.hardware.pantilt.camera_service as camera_service

    importlib.reload(camera_service)
    return camera_service


def test_start_stop_stream_configures_camera_and_encoder():
    camera_service = import_service()
    servos = MagicMock()
    service = camera_service.PanTiltCameraService(
        servos=servos,
        resolution=(640, 480),
        framerate=24,
        pan_offset=5.0,
        tilt_offset=-2.0,
    )

    destination = object()
    service.command_servos(10.0, 4.0)
    service.start_stream(destination)

    assert service.is_streaming is True
    assert service._camera is not None
    camera = service._camera
    assert camera.configured is not None
    assert camera.configured["main"]["size"] == (640, 480)
    assert camera.configured["controls"]["FrameDurationLimits"] == (41666, 41666)
    servos.move_to.assert_has_calls([call(15.0, 2.0), call(15.0, 2.0)])

    service.stop_stream()
    assert service.is_streaming is False
    assert camera.stopped is True
    assert camera.closed is True


def test_servo_alignment_applies_offsets_on_commands():
    camera_service = import_service()
    servos = MagicMock()
    service = camera_service.PanTiltCameraService(servos=servos, pan_offset=1.5, tilt_offset=-0.5)

    service.command_servos(-12.0, 22.0)
    servos.move_to.assert_called_once_with(-10.5, 21.5)

    service.command_servos(0.0, 0.0)
    assert servos.move_to.call_args_list[-1] == call(1.5, -0.5)


def test_get_frame_returns_live_when_streaming_and_fallback_otherwise():
    camera_service = import_service()
    servos = MagicMock()
    still_image = b"fallback"
    fallback_provider = MagicMock(return_value=still_image)
    service = camera_service.PanTiltCameraService(servos=servos, still_image_provider=fallback_provider)

    frame_without_stream = service.get_frame()
    assert frame_without_stream == still_image
    fallback_provider.assert_called_once()

    service.start_stream(object())
    frame_with_stream = service.get_frame()
    assert frame_with_stream == b"live-frame"
    assert fallback_provider.call_count == 1

    service.stop_stream()
    assert service.get_frame() == still_image
    assert fallback_provider.call_count == 2


def test_start_stream_failure_triggers_fallback_and_error(monkeypatch):
    camera_service = import_service()
    servos = MagicMock()
    still_image = b"fallback"

    class FailingCamera:
        def __init__(self) -> None:
            self.closed = False

        def create_video_configuration(self, **kwargs):
            return {"main": {}, "controls": {}}

        def configure(self, config):
            self.config = config

        def start_recording(self, encoder, output):
            raise RuntimeError("libcamera pipeline failure")

        def stop_recording(self):
            raise AssertionError("stop_recording should not be called after failure")

        def close(self):
            self.closed = True

        def capture_file(self, fileobj, format="jpeg"):
            fileobj.write(b"should-not-be-used")

    failing_module = SimpleNamespace(Picamera2=FailingCamera, MjpegEncoder=lambda: object())
    outputs_module = SimpleNamespace(FileOutput=lambda destination: object())

    monkeypatch.setitem(sys.modules, "picamera2", failing_module)
    monkeypatch.setitem(sys.modules, "picamera2.outputs", outputs_module)
    importlib.invalidate_caches()

    camera_service = import_service()

    service = camera_service.PanTiltCameraService(
        servos=servos,
        still_image_provider=lambda: still_image,
        resolution=(320, 240),
        framerate=30,
    )

    with pytest.raises(camera_service.StreamError):
        service.start_stream(object())

    assert service.is_streaming is False
    assert service.last_error is not None
    assert still_image == service.get_frame()
    assert service._camera is None

    monkeypatch.delitem(sys.modules, "picamera2")
    monkeypatch.delitem(sys.modules, "picamera2.outputs")
    importlib.invalidate_caches()
