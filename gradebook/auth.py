"""Authentication manager for GradeBook Pro."""

import hashlib
from typing import Optional

from .models import User
from .database import DatabaseManager


class AuthManager:
    """Handles user registration, login, and password hashing."""

    def __init__(self, db: DatabaseManager):
        """Initialize with a DatabaseManager instance."""
        self.db = db
        self.current_user: Optional[User] = None

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def register_user(self, username: str, password: str) -> Optional[User]:
        """
        Register a new user.

        Returns the new User object, or None if the username is taken
        or inputs are invalid.
        """
        username = username.strip()
        if not username or not password:
            return None
        if len(username) < 3:
            return None
        if len(password) < 4:
            return None
        # Check uniqueness
        if self.db.get_user_by_username(username):
            return None
        try:
            pw_hash = self.hash_password(password)
            user = self.db.create_user(username, pw_hash)
            # Create a default grade scale for the user
            self.db.create_default_scale(user.id)  # type: ignore[arg-type]
            return user
        except Exception:
            return None

    def login(self, username: str, password: str) -> Optional[User]:
        """
        Attempt to log in.

        Returns the User on success, or None on failure.
        """
        username = username.strip()
        user = self.db.get_user_by_username(username)
        if user is None:
            return None
        if user.password_hash == self.hash_password(password):
            self.current_user = user
            return user
        return None

    def logout(self) -> None:
        """Log out the current user."""
        self.current_user = None

    @staticmethod
    def hash_password(password: str) -> str:
        """Return the SHA-256 hex digest of the given password."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def is_logged_in(self) -> bool:
        """Return True if a user is currently logged in."""
        return self.current_user is not None
