from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict


@dataclass
class ThrottleState:
    current_gap_seconds: float
    blocked_until: datetime | None = None
    consecutive_successes: int = 0
    total_blocks_seen: int = 0


class AIMDThrottler:
    def __init__(
        self,
        base_gap_seconds: float = 7.0,
        max_gap_seconds: float = 3600.0,
        block_multiplier: float = 2.0,
        success_decay: float = 0.9,
        blackout_hours: float = 24.0,
        jitter_percent: float = 0.2,
    ) -> None:
        self.base_gap = base_gap_seconds
        self.max_gap = max_gap_seconds
        self.block_multiplier = block_multiplier
        self.success_decay = success_decay
        self.blackout_hours = blackout_hours
        self.jitter_percent = jitter_percent
        self._platforms: Dict[str, ThrottleState] = {}

    def _get_or_init(self, platform: str) -> ThrottleState:
        if platform not in self._platforms:
            self._platforms[platform] = ThrottleState(current_gap_seconds=self.base_gap)
        return self._platforms[platform]

    def is_blocked(self, platform: str, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        state = self._platforms.get(platform)
        if not state or not state.blocked_until:
            return False
        if now < state.blocked_until:
            return True
        state.blocked_until = None
        state.current_gap_seconds = self.base_gap
        state.consecutive_successes = 0
        return False

    def current_gap(self, platform: str) -> float:
        if self.is_blocked(platform):
            return self.max_gap
        return self._get_or_init(platform).current_gap_seconds

    def wait_time(self, platform: str) -> float:
        gap = self.current_gap(platform)
        return gap * random.uniform(1.0 - self.jitter_percent, 1.0 + self.jitter_percent)

    def record_success(self, platform: str) -> None:
        state = self._get_or_init(platform)
        state.consecutive_successes += 1
        state.current_gap_seconds = max(self.base_gap, state.current_gap_seconds * self.success_decay)

    def record_block(self, platform: str, reason: str = "") -> None:
        state = self._get_or_init(platform)
        state.total_blocks_seen += 1
        state.consecutive_successes = 0
        state.current_gap_seconds = min(self.max_gap, state.current_gap_seconds * self.block_multiplier)
        state.blocked_until = datetime.utcnow() + timedelta(hours=self.blackout_hours)

    def wait_before_submit(self, platform: str) -> float:
        if self.is_blocked(platform):
            return 0.0
        wait_s = self.wait_time(platform)
        time.sleep(wait_s)
        return wait_s

    def status(self) -> Dict[str, dict]:
        now = datetime.utcnow()
        out: Dict[str, dict] = {}
        for p, s in self._platforms.items():
            out[p] = {
                "current_gap_s": s.current_gap_seconds,
                "blocked": s.blocked_until is not None and now < s.blocked_until,
                "blocked_until": s.blocked_until.isoformat() if s.blocked_until else None,
                "consecutive_successes": s.consecutive_successes,
                "total_blocks_seen": s.total_blocks_seen,
            }
        return out
