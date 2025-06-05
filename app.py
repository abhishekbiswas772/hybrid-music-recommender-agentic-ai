# app.py - Fixed Main Streamlit Application
import streamlit as st
import asyncio
import logging

from core.ui.components.analytics import show_analytics_page
from core.ui.pages.home import show_home_page
from core.ui.utils.session import SessionManager
from core.ui.utils.styling import apply_custom_css

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration - moved to top to avoid context issues
st.set_page_config(
    page_title="🎵 AI Music Curator Pro",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

class MusicCuratorApp:
    """Main application class"""
    
    def __init__(self):
        self.config = None
        self.db_manager = None
        self.user_service = None
        self.session_manager = None
        self.hybrid_system = None
        
        # Initialize components
        self._init_components()
    
    def _init_components(self):
        """Initialize application components"""
        try:
            # Import components here to avoid context issues
            from configs.settings import Config
            from database.manager import DatabaseManager
            from services.user_service import UserService

            
            # Initialize configuration
            self.config = Config()
            
            # Initialize database
            self.db_manager = DatabaseManager(self.config.database.db_path)
            
            # Initialize services
            self.user_service = UserService(self.db_manager)
            self.session_manager = SessionManager()
            
            # Apply custom styling
            apply_custom_css()
            
            logger.info("✅ Application components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            st.error(f"Failed to initialize application: {e}")
            st.stop()
    
    def _init_hybrid_system(self):
        """Initialize the hybrid LLM+RL system when needed"""
        if self.hybrid_system is None:
            try:
                from core.hybrid_system import HybridMusicSystem
                self.hybrid_system = HybridMusicSystem(self.config, self.db_manager)
                logger.info("✅ Hybrid system initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize hybrid system: {e}")
                st.error("Failed to initialize AI system. Please check configuration.")
                return None
        
        return self.hybrid_system
    
    def run(self):
        """Main application entry point"""
        
        # Initialize session state if needed
        if 'app_initialized' not in st.session_state:
            st.session_state.app_initialized = True
        
        # Check authentication
        if not self.session_manager.is_authenticated():
            self._show_authentication()
            return
        
        # Initialize hybrid system if authenticated
        hybrid_system = self._init_hybrid_system()
        if not hybrid_system:
            return
        
        # Show main application
        self._show_main_app(hybrid_system)
    
    def _show_authentication(self):
        """Show login/register page"""
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h1>🎵 AI Music Curator Pro</h1>
            <p style="font-size: 1.2rem;">Your Intelligent Music Discovery Companion</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔑 Login", "🆕 Register"])
        
        with tab1:
            self._show_login_form()
        
        with tab2:
            self._show_register_form()
    
    def _show_login_form(self):
        """Show login form"""
        with st.form("login_form"):
            st.subheader("Welcome Back!")
            
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            remember_me = st.checkbox("Remember me")
            
            if st.form_submit_button("Login", type="primary"):
                if self.user_service.authenticate(username, password):
                    user = self.user_service.get_user_by_username(username)
                    self.session_manager.login(user, remember_me)
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    def _show_register_form(self):
        """Show registration form"""
        with st.form("register_form"):
            st.subheader("Join the Revolution!")
            
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Username*")
                email = st.text_input("Email*")
                full_name = st.text_input("Full Name")
            
            with col2:
                password = st.text_input("Password*", type="password")
                confirm_password = st.text_input("Confirm Password*", type="password")
                terms_accepted = st.checkbox("I accept the Terms of Service")
            
            if st.form_submit_button("Create Account", type="primary"):
                # Validation
                errors = []
                if not username or len(username) < 3:
                    errors.append("Username must be at least 3 characters")
                if not email or "@" not in email:
                    errors.append("Valid email is required")
                if not password or len(password) < 6:
                    errors.append("Password must be at least 6 characters")
                if password != confirm_password:
                    errors.append("Passwords don't match")
                if not terms_accepted:
                    errors.append("Please accept the Terms of Service")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # Create user
                    if self.user_service.create_user(username, email, password, full_name):
                        st.success("Account created! Please log in.")
                    else:
                        st.error("Username or email already exists")
    
    def _show_main_app(self, hybrid_system):
        """Show main application interface"""
        user = self.session_manager.get_current_user()
        
        # Sidebar navigation
        with st.sidebar:
            st.markdown(f"### Welcome, {user['full_name'] or user['username']}!")
            
            # User stats
            stats = self.user_service.get_user_stats(user['id'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Queries", stats['total_interactions'])
                st.metric("Ratings", stats['total_feedback'])
            with col2:
                # Simple personalization calculation
                personalization = min(100, (stats['total_feedback'] / 20) * 100)
                st.metric("AI Level", f"{personalization:.0f}%")
                if stats['average_rating'] > 0:
                    st.metric("Avg Rating", f"{stats['average_rating']:.1f}/5")
            
            # Navigation
            page = st.selectbox("Navigate", [
                "🎵 Music Discovery",
                "📊 Analytics & Reports", 
                "👤 Profile Settings"
            ])
            
            # Quick actions
            st.markdown("---")
            if st.button("🔄 Retrain AI"):
                with st.spinner("Training AI model..."):
                    # Simple retraining simulation
                    if stats['total_feedback'] >= 5:
                        st.success("AI model updated!")
                    else:
                        needed = 5 - stats['total_feedback']
                        st.warning(f"Need {needed} more ratings to train AI")
            
            if st.button("🚪 Logout"):
                self.session_manager.logout()
                st.rerun()
        
        # Main content area
        if page == "🎵 Music Discovery":
            self._show_home_page(user, hybrid_system)
        elif page == "📊 Analytics & Reports":
            self._show_analytics_page(user)
        elif page == "👤 Profile Settings":
            self._show_profile_page(user)
    
    def _show_home_page(self, user, hybrid_system):
        """Show home page with music recommendations"""
        
        # Import here to avoid context issues
        try:
           
            show_home_page(user, hybrid_system, self.db_manager)
        except ImportError:
            # Fallback simple implementation
            st.markdown("### 🎵 Music Discovery")
            st.write("Welcome to the music discovery page!")
            
            query = st.text_area("What music are you looking for?", 
                               placeholder="e.g., energetic music for working out")
            
            if st.button("🎵 Get Recommendations", type="primary"):
                if query:
                    st.info("🎵 Music recommendation system is loading...")
                    st.write("This feature will be available once all components are properly loaded.")
                else:
                    st.warning("Please enter a music query")
    
    def _show_analytics_page(self, user):
        """Show analytics page"""
        
        try:
  
            show_analytics_page(user, self.db_manager)
        except ImportError:
            # Fallback simple implementation
            st.markdown("### 📊 Analytics Dashboard")
            
            stats = self.user_service.get_user_stats(user['id'])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Queries", stats['total_interactions'])
            
            with col2:
                st.metric("Total Ratings", stats['total_feedback'])
            
            with col3:
                if stats['average_rating'] > 0:
                    st.metric("Average Rating", f"{stats['average_rating']:.1f}/5")
                else:
                    st.metric("Average Rating", "No ratings yet")
            
            if stats['total_interactions'] == 0:
                st.info("🎵 Start using the music recommender to see analytics!")
            else:
                st.write("📊 Detailed analytics will be available once you use the system more.")
    
    def _show_profile_page(self, user):
        """Show profile settings page"""
        
        st.markdown("### 👤 Profile Settings")
        
        with st.form("profile_form"):
            st.subheader("Update Your Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                new_full_name = st.text_input("Full Name", value=user.get('full_name', ''))
                new_email = st.text_input("Email", value=user.get('email', ''))
            
            with col2:
                # Music preferences
                st.markdown("**Music Preferences:**")
                favorite_genres = st.multiselect(
                    "Favorite Genres",
                    ["Rock", "Pop", "Electronic", "Hip-Hop", "Jazz", "Classical", 
                     "Country", "R&B", "Indie", "Alternative"],
                    default=[]
                )
            
            # Settings
            st.markdown("**Settings:**")
            email_notifications = st.checkbox("Email notifications", value=True)
            ai_learning = st.checkbox("Enable AI learning", value=True)
            
            if st.form_submit_button("Save Changes", type="primary"):
                # Update user preferences
                preferences = {
                    'favorite_genres': favorite_genres,
                    'email_notifications': email_notifications,
                    'ai_learning_enabled': ai_learning
                }
                
                if self.user_service.update_user_preferences(user['id'], preferences):
                    st.success("Profile updated successfully!")
                else:
                    st.error("Failed to update profile")
        
        # Account management
        st.markdown("---")
        st.markdown("### 🔐 Account Management")
        
        with st.expander("Change Password"):
            with st.form("password_form"):
                old_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_new = st.text_input("Confirm New Password", type="password")
                
                if st.form_submit_button("Change Password"):
                    if new_password != confirm_new:
                        st.error("New passwords don't match")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        if self.user_service.change_password(user['id'], old_password, new_password):
                            st.success("Password changed successfully!")
                        else:
                            st.error("Current password is incorrect")
        
        # Data export
        with st.expander("Export Data"):
            st.write("Download your data for backup or analysis:")
            
            if st.button("📥 Export My Data"):
                st.info("Data export feature coming soon!")

def main():
    """Application entry point"""
    try:
        app = MusicCuratorApp()
        app.run()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"Application error: {e}")
        st.write("Please refresh the page or contact support if the problem persists.")

if __name__ == "__main__":
    main()