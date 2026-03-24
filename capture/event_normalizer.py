from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from contracts.observed_action import (
    Artifacts,
    BoundingBox,
    ObservedAction,
    RawTarget,
    RelativeBox,
    ScreenSnapshot,
    StateChange,
)


class EventNormalizer:
    def normalize(self, raw_event: dict) -> ObservedAction:
        bbox = None
        raw_bbox = raw_event.get("bbox") or {}
        if raw_bbox:
            bbox = BoundingBox(
                x=float(raw_bbox.get("x", 0)),
                y=float(raw_bbox.get("y", 0)),
                w=float(raw_bbox.get("w", 0)),
                h=float(raw_bbox.get("h", 0)),
            )

        coords_rel = None
        raw_coords = raw_event.get("coords_rel") or {}
        if raw_coords:
            coords_rel = RelativeBox(
                x_pct=float(raw_coords.get("x_pct", 0.5)),
                y_pct=float(raw_coords.get("y_pct", 0.5)),
                w_pct=float(raw_coords.get("w_pct", 0.05)),
                h_pct=float(raw_coords.get("h_pct", 0.05)),
            )

        screen_before = ScreenSnapshot(**(raw_event.get("screen_before") or {}))
        screen_after_payload = raw_event.get("screen_after")
        screen_after = ScreenSnapshot(**screen_after_payload) if screen_after_payload else None

        state_change_payload = raw_event.get("state_change")
        state_change = StateChange(**state_change_payload) if state_change_payload else None

        artifacts = Artifacts(**(raw_event.get("artifacts") or {}))

        raw_target = RawTarget(
            selector=raw_event.get("selector"),
            tag=raw_event.get("tag"),
            text=raw_event.get("text"),
            role=raw_event.get("role"),
            name=raw_event.get("name"),
            aria_label=raw_event.get("aria_label"),
            iframe_hint=raw_event.get("iframe_hint"),
            bbox=bbox,
            coords_rel=coords_rel,
        )

        return ObservedAction(
            event_id=raw_event.get("event_id") or f"obs_{uuid4().hex[:12]}",
            timestamp=raw_event.get("timestamp") or datetime.now(timezone.utc),
            action_type=raw_event["action_type"],
            raw_target=raw_target,
            typed_value=raw_event.get("typed_value"),
            screen_before=screen_before,
            screen_after=screen_after,
            state_change=state_change,
            artifacts=artifacts,
            capture_confidence=float(raw_event.get("capture_confidence", 0.5)),
            risk_class=raw_event.get("risk_class", "low"),
        )