from __future__ import annotations


class ComplianceViolation(RuntimeError):
    def __init__(self, violations: list[str]) -> None:
        self.violations = list(violations)
        super().__init__("Hard compliance violations: " + "; ".join(violations))
