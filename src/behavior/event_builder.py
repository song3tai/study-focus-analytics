"""Translate state transitions into structured events."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.enums import BehaviorState, EventType
from src.core.models import BehaviorEvent, BehaviorStateSnapshot


@dataclass
class EventBuilder:
    """Emit one event when the debounced state changes."""

    def build(self, snapshot: BehaviorStateSnapshot) -> BehaviorEvent | None:
        if snapshot.previous_state is None:
            return None

        event_type = EventType.STATE_CHANGED
        message = f"state changed to {snapshot.state.value}"

        if snapshot.state == BehaviorState.AWAY:
            event_type = EventType.AWAY_STARTED
            message = "user left the study/work area"
        elif snapshot.previous_state == BehaviorState.AWAY:
            event_type = EventType.AWAY_ENDED
            message = "user returned to the study/work area"
        elif snapshot.state == BehaviorState.STUDYING:
            event_type = EventType.STUDYING_STARTED
            message = "studying state confirmed"
        elif snapshot.previous_state == BehaviorState.STUDYING:
            event_type = EventType.STUDYING_ENDED
            message = "studying state ended"

        return BehaviorEvent(
            event_type=event_type,
            frame_index=snapshot.frame_index,
            timestamp_seconds=snapshot.timestamp_seconds,
            state=snapshot.state,
            message=message,
        )
