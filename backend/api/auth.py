"""Auth & authorization dependencies for the PE Investment Platform.

Phase 4: Authentication/authorization on all endpoints.

For MVP: Simple API-key based auth + role inference from header.
Production: JWT tokens, OAuth2, etc.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """User roles in the PE investment platform."""
    PARTNER = "partner"
    VP = "vp"
    ASSOCIATE = "associate"
    SYSTEM = "system"


class UserContext:
    """Authenticated user context passed to all endpoints."""

    def __init__(self, user_id: str, role: UserRole, email: str | None = None):
        self.user_id = user_id
        self.role = role
        self.email = email

    def has_role(self, *roles: UserRole) -> bool:
        return self.role in roles

    def is_partner(self) -> bool:
        return self.role == UserRole.PARTNER

    def is_vp(self) -> bool:
        return self.role == UserRole.VP

    def is_associate(self) -> bool:
        return self.role == UserRole.ASSOCIATE

    def can_view_raw_data(self) -> bool:
        return self.role in (UserRole.ASSOCIATE, UserRole.SYSTEM)

    def can_edit_views(self) -> bool:
        return self.role in (UserRole.ASSOCIATE, UserRole.VP, UserRole.PARTNER)

    def can_finalize_views(self) -> bool:
        return self.role in (UserRole.VP, UserRole.PARTNER)

    def can_override_weights(self) -> bool:
        return self.role in (UserRole.VP, UserRole.PARTNER)

    def to_dict(self) -> dict[str, Any]:
        return {"user_id": self.user_id, "role": self.role.value, "email": self.email}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    request: Request | None = None,
) -> UserContext:
    """Resolve the current user from API token or development header.

    Phase 4 MVP: Reads from X-User-Id and X-User-Role headers for dev,
    or validates a bearer token in production.
    """
    # Development mode: infer from headers
    if request is not None:
        user_id = request.headers.get("X-User-Id", "dev-user")
        role_str = request.headers.get("X-User-Role", "associate")

        try:
            role = UserRole(role_str.lower())
        except ValueError:
            role = UserRole.ASSOCIATE

        return UserContext(user_id=user_id, role=role, email=f"{user_id}@pe.com")

    # Production: validate bearer token
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # For MVP, accept any non-empty token and default to associate
    # Production: verify JWT / OAuth2 token here
    return UserContext(user_id="api-user", role=UserRole.ASSOCIATE, email="api-user@pe.com")


async def require_role(*roles: UserRole) -> Any:
    """Dependency factory that requires specific roles."""
    async def checker(user: UserContext = Depends(get_current_user)) -> UserContext:
        if not user.has_role(*roles):
            raise HTTPException(
                status_code=403,
                detail=f"Required role: {', '.join(r.value for r in roles)}. Your role: {user.role.value}"
            )
        return user
    return checker
