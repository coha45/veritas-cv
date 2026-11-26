"""Per-road traffic states with optional two-output Raspberry Pi modules."""

import os
import platform

from Enums import TrafficState


STATE_PATTERN = {
    TrafficState.RED: (True, False),
    TrafficState.GREEN: (False, True),
}


def _enabled(value):
    return value.strip().lower() in {"1", "true", "yes", "on"}


class TrafficOutput:
    """Drive a configured pair of GPIO outputs for each road checker.

    The pair encodes RED=10 and GREEN=01. GPIO output is disabled by default.
    """

    def __init__(self, checkers):
        self.devices = {}
        self.states = {checker["id"]: TrafficState.RED for checker in checkers}
        self.gpio_enabled = _enabled(os.getenv("VERITAS_GPIO", "0"))

        if not self.gpio_enabled:
            print("[TRAFFIC] GPIO output disabled; using abstract road states only")
            return

        if platform.system() != "Linux":
            raise RuntimeError("VERITAS_GPIO=1 is only supported on Raspberry Pi OS/Linux")

        all_pins = [pin for checker in checkers for pin in checker["gpio_pins"]]
        if any(len(checker["gpio_pins"]) != 2 for checker in checkers):
            raise ValueError("Each traffic checker must have exactly two GPIO pins")
        if len(set(all_pins)) != len(all_pins):
            raise ValueError("Every traffic LED must use a different GPIO pin")

        try:
            from gpiozero import LED
        except ImportError as error:
            raise RuntimeError(
                "GPIO output requires gpiozero. Install it with `python -m pip install gpiozero`."
            ) from error

        active_high = _enabled(os.getenv("VERITAS_GPIO_ACTIVE_HIGH", "1"))
        try:
            for checker in checkers:
                checker_id = checker["id"]
                self.devices[checker_id] = []
                for pin in checker["gpio_pins"]:
                    self.devices[checker_id].append(
                        LED(pin, active_high=active_high, initial_value=False)
                    )
        except Exception:
            self.close()
            raise

        print("[TRAFFIC] GPIO enabled (BCM, LED A/LED B encoding):")
        for checker in checkers:
            print(
                f"  {checker['label']}: "
                f"GPIO {checker['gpio_pins'][0]} / {checker['gpio_pins'][1]}"
            )

    def set_state(self, checker_id, state):
        if checker_id not in self.states:
            raise ValueError(f"Unknown traffic checker: {checker_id}")
        if isinstance(state, str):
            state = TrafficState[state.strip().upper()]
        if not isinstance(state, TrafficState):
            raise ValueError("state must be RED or GREEN")

        try:
            for device, active in zip(self.devices.get(checker_id, []), STATE_PATTERN[state]):
                if active:
                    device.on()
                else:
                    device.off()
        except Exception:
            for device in self.devices.get(checker_id, []):
                try:
                    device.off()
                except Exception:
                    pass
            raise

        self.states[checker_id] = state
        return state

    def close(self):
        for devices in self.devices.values():
            for device in devices:
                try:
                    device.off()
                    device.close()
                except Exception:
                    pass
        self.devices.clear()
