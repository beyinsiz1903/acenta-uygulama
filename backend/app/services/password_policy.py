"""Password policy enforcement for Enterprise Security (E2.3)."""
from __future__ import annotations

import re
from typing import List, Optional


class PasswordPolicyError(Exception):
    def __init__(self, violations: List[str]):
        self.violations = violations
        super().__init__(f"Password policy violations: {', '.join(violations)}")


def validate_password(password: str) -> Optional[List[str]]:
    """Validate password against enterprise policy.
    Returns list of violations, or None if valid.
    
    Policy:
    - Minimum 10 characters
    - At least 1 uppercase letter
    - At least 1 number
    - At least 1 special character
    """
    violations: List[str] = []

    if len(password) < 10:
        violations.append("Password must be at least 10 characters long")
    if not re.search(r'[A-Z]', password):
        violations.append("Password must contain at least 1 uppercase letter")
    if not re.search(r'[0-9]', password):
        violations.append("Password must contain at least 1 number")
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?~`]', password):
        violations.append("Password must contain at least 1 special character")

    return violations if violations else None


def enforce_password_policy(password: str) -> None:
    """Raise PasswordPolicyError if password is weak."""
    violations = validate_password(password)
    if violations:
        raise PasswordPolicyError(violations)
