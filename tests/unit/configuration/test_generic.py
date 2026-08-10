from dataclasses import dataclass

from configuration.generic import Settings


def test_settings_factory_is_cached_per_settings_class() -> None:
    @dataclass(frozen=True)
    class ExampleSettings(Settings):
        value: str = "example"

    assert ExampleSettings.get_settings() is ExampleSettings.get_settings()
