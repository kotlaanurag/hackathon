"""Authentication module for handling user login and validation."""

import re
import hashlib
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class User:
    """User data class."""
    username: str
    email: str
    password_hash: str
    is_active: bool = True


class PasswordValidator:
    """Validates passwords against security requirements."""
    
    def __init__(
        self,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True
    ):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    def validate(self, password: str) -> Tuple[bool, list]:
        """
        Validate a password against all requirements.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.require_digit and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if self.require_special and not any(c in self.special_chars for c in password):
            errors.append(f"Password must contain at least one special character ({self.special_chars})")
        
        return len(errors) == 0, errors


class AuthenticationService:
    """Handles user authentication."""
    
    def __init__(self):
        self.password_validator = PasswordValidator()
        self._users: dict = {}  # In-memory user store (replace with database)
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username: str, email: str, password: str) -> Tuple[bool, str]:
        """
        Register a new user.
        
        Returns:
            Tuple of (success, message)
        """
        # Validate password
        is_valid, errors = self.password_validator.validate(password)
        if not is_valid:
            return False, "; ".join(errors)
        
        # Check if user exists
        if username in self._users:
            return False, "Username already exists"
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=self.hash_password(password)
        )
        self._users[username] = user
        
        return True, "User registered successfully"
    
    def login(self, username: str, password: str) -> Tuple[bool, Optional[User], str]:
        """
        Authenticate a user.
        
        Returns:
            Tuple of (success, user or None, message)
        """
        user = self._users.get(username)
        
        if not user:
            return False, None, "Invalid username or password"
        
        if not user.is_active:
            return False, None, "User account is disabled"
        
        if user.password_hash != self.hash_password(password):
            return False, None, "Invalid username or password"
        
        return True, user, "Login successful"
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change a user's password.
        
        Returns:
            Tuple of (success, message)
        """
        # Verify current credentials
        success, user, _ = self.login(username, old_password)
        if not success:
            return False, "Current password is incorrect"
        
        # Validate new password
        is_valid, errors = self.password_validator.validate(new_password)
        if not is_valid:
            return False, "; ".join(errors)
        
        # Update password
        user.password_hash = self.hash_password(new_password)
        return True, "Password changed successfully"
