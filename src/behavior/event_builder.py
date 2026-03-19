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

        event_type = EventType.SESSION_STARTED
        message = f"state changed to {snapshot.current_state.value}"

        if snapshot.current_state == BehaviorState.AWAY:
            event_type = EventType.AWAY_STARTED
            message = "user left the study/work area"
        elif snapshot.previous_state == BehaviorState.AWAY:
            event_type = EventType.AWAY_ENDED
            message = "user returned to the study/work area"
        elif snapshot.previous_state == BehaviorState.UNKNOWN:
            event_type = EventType.SESSION_STARTED
            message = "analysis session entered a stable state"
        elif snapshot.current_state == BehaviorState.UNKNOWN:
            event_type = EventType.SESSION_ENDED
            message = "analysis session returned to unknown state"

        return BehaviorEvent(
            event_type=event_type,
            frame_id=snapshot.frame_id,
            timestamp=snapshot.timestamp,
            state_before=snapshot.previous_state,
            state_after=snapshot.current_state,
            message=message,
        )
