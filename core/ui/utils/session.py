import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Optional
import hashlib
import secrets

class SessionManager:
    """Manage user sessions and authentication"""
    
    def __init__(self):
        self.session_timeout = timedelta(hours=8)
        
        # Initialize session state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_data' not in st.session_state:
            st.session_state.user_data = None
        if 'session_token' not in st.session_state:
            st.session_state.session_token = None
        if 'login_time' not in st.session_state:
            st.session_state.login_time = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated and session is valid"""
        
        if not st.session_state.authenticated:
            return False
        
        if not st.session_state.login_time:
            return False
        
        # Check session timeout
        login_time = datetime.fromisoformat(st.session_state.login_time)
        if datetime.now() - login_time > self.session_timeout:
            self.logout()
            return False
        
        return True
    
    def login(self, user_data: Dict, remember_me: bool = False):
        """Login user and create session"""
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        
        # Update session state
        st.session_state.authenticated = True
        st.session_state.user_data = user_data
        st.session_state.session_token = session_token
        st.session_state.login_time = datetime.now().isoformat()
        
        # Extend session if remember me
        if remember_me:
            self.session_timeout = timedelta(days=30)
    
    def logout(self):
        """Logout user and clear session"""
        
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.session_state.session_token = None
        st.session_state.login_time = None
        
        # Clear recommendation data
        for key in list(st.session_state.keys()):
            if key.startswith('current_recommendations'):
                del st.session_state[key]
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current authenticated user"""
        
        if self.is_authenticated():
            return st.session_state.user_data
        return None
    
    def update_user_data(self, user_data: Dict):
        """Update user data in session"""
        
        if self.is_authenticated():
            st.session_state.user_data = user_data
    
    def extend_session(self):
        """Extend current session"""
        
        if self.is_authenticated():
            st.session_state.login_time = datetime.now().isoformat()
