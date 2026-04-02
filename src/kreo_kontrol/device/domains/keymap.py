from __future__ import annotations

from pydantic import BaseModel


class KeyAssignment(BaseModel):
    position: str
    action: str
    fn_action: str | None = None

