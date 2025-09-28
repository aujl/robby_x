import pytest

from src.api.control_service.config import ControlServiceConfig, RateLimitSettings

pytestmark = pytest.mark.camjam_unit


def test_rate_limit_settings_validation() -> None:
    with pytest.raises(ValueError):
        RateLimitSettings(rate_per_second=0.0, burst=1)

    with pytest.raises(ValueError):
        RateLimitSettings(rate_per_second=1.0, burst=0)


def test_control_service_config_snapshot_and_validation() -> None:
    config = ControlServiceConfig(
        api_keys={"alpha"},
        allowed_networks=["127.0.0.0/8", "10.0.0.0/8"],
        queue_maxsize=8,
    )

    assert isinstance(config.allowed_networks, tuple)
    snapshot = config.snapshot()
    assert snapshot["queue_maxsize"] == 8
    assert snapshot["ingress_rate_limit"]["rate_per_second"] == pytest.approx(5.0)

    with pytest.raises(ValueError):
        ControlServiceConfig(api_keys=set())

    with pytest.raises(ValueError):
        ControlServiceConfig(api_keys={"beta"}, queue_maxsize=0)
