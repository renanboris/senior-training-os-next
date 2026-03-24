from __future__ import annotations


class LegacyBridge:
    def __init__(self, legacy_json_steps: list[dict] | None = None):
        self.legacy_json_steps = legacy_json_steps or []

    def get_step_for_event(self, event_id: str, index: int | None = None) -> dict | None:
        if index is not None and 0 <= index < len(self.legacy_json_steps):
            return self.legacy_json_steps[index]

        for step in self.legacy_json_steps:
            if step.get("source_event_id") == event_id:
                return step
        return None