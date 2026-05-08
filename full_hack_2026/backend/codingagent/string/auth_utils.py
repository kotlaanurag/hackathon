"""Authentication utility functions."""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional


def generate_token(length: int = 32) -> str:
    """Generate a secure random token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return secrets.token_urlsafe(32)


class SessionManager:
    """Manages user sessions."""
    
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: dict = {}
        self.timeout = timedelta(minutes=session_timeout_minutes)
    
    def create_session(self, user_id: str) -> str:
        """Create a new session for a user."""
        session_id = generate_session_id()
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "last_activity": datetime.now()
        }
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[str]:
        """
        Validate a session and return the user_id if valid.
        
        Returns:
            user_id if session is valid, None otherwise
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        # Check if session has expired
        if datetime.now() - session["last_activity"] > self.timeout:
            self.destroy_session(session_id)
            return None
        
        # Update last activity
        session["last_activity"] = datetime.now()
        return session["user_id"]
    
    def destroy_session(self, session_id: str) -> bool:
        """Destroy a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions. Returns count of removed sessions."""
        now = datetime.now()
        expired = [
            sid for sid, data in self.sessions.items()
            if now - data["last_activity"] > self.timeout
        ]
        for sid in expired:
            del self.sessions[sid]
        return len(expired)
