"""Abstract traffic state with an optional Raspberry Pi GPIO output."""

import os
import platform

from Enums import TrafficState


def _enabled(value):
    return value.strip().lower() in {"1", "true", "yes", "on"}


class TrafficOutput:
    """Track a logical light state and optionally drive three GPIO outputs.

    GPIO output is disabled by default. Enable it with VERITAS_GPIO=1 and
    provide distinct BCM pin numbers in VERITAS_RED_PIN, VERITAS_YELLOW_PIN,
    and VERITAS_GREEN_PIN.
    """

    def __init__(self):
        self.devices = {}
        self.state = None
        self.gpio_enabled = _enabled(os.getenv("VERITAS_GPIO", "0"))

        if not self.gpio_enabled:
            print("[TRAFFIC] GPIO output disabled; using abstract state only")
            return

        if platform.system() != "Linux":
            raise RuntimeError("VERITAS_GPIO=1 is only supported on Raspberry Pi OS/Linux")

        pin_names = {
            TrafficState.RED: "VERITAS_RED_PIN",
            TrafficState.YELLOW: "VERITAS_YELLOW_PIN",
            TrafficState.GREEN: "VERITAS_GREEN_PIN",
        }
        missing = [name for name in pin_names.values() if not os.getenv(name)]
        if missing:
            raise RuntimeError("GPIO enabled but missing pin settings: " + ", ".join(missing))

        pins = {state: int(os.environ[name]) for state, name in pin_names.items()}
        if len(set(pins.values())) != len(pins):
            raise RuntimeError("Red, yellow, and green GPIO pins must be different")

        try:
            from gpiozero import LED
        except ImportError as error:
            raise RuntimeError(
                "GPIO output requires gpiozero. Install it with `python -m pip install gpiozero`."
            ) from error

        active_high = _enabled(os.getenv("VERITAS_GPIO_ACTIVE_HIGH", "1"))
        try:
            for state, pin in pins.items():
                self.devices[state] = LED(
                    pin,
                    active_high=active_high,
                    initial_value=False,
                )
        except Exception:
            self.close()
            raise

        print(
            "[TRAFFIC] GPIO enabled (BCM): "
            + ", ".join(
                f"{state.name}={pins[state]}" for state in pin_names
            )
        )

    def set_state(self, state):
        if isinstance(state, str):
            state = TrafficState[state.strip().upper()]
        if not isinstance(state, TrafficState):
            raise ValueError("state must be RED, YELLOW, or GREEN")

        try:
            for device in self.devices.values():
                device.off()
            if state in self.devices:
                self.devices[state].on()
        except Exception:
            # Leave all outputs inactive if switching fails partway through.
            for device in self.devices.values():
                try:
                    device.off()
                except Exception:
                    pass
            raise

        self.state = state
        return state

    def close(self):
        for device in self.devices.values():
            try:
                device.off()
                device.close()
            except Exception:
                pass
        self.devices.clear()
