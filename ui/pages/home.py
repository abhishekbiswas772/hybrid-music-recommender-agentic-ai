import streamlit as st
import asyncio
from typing import Dict, List
from datetime import datetime

from core.hybrid_system import RecommendationRequest
from ui.components.audio_player import AudioPlayer
from ui.components.track_card import TrackCard

class HomePage:
    def __init__(self):
        self.audio_player = AudioPlayer()
        self.track_card = TrackCard(self.audio_player)
    
    def show_home_page(self, user: Dict, hybrid_system, db_manager):
        st.markdown(f"### 🎵 Welcome back, {user['full_name'] or user['username']}!")
        st.markdown("What music matches your mood today?")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._show_query_interface(user, hybrid_system)
        
        with col2:
            self._show_context_panel(user, hybrid_system)
        
        # Show recommendations if available
        if hasattr(st.session_state, 'current_recommendations'):
            self._show_recommendations(user, hybrid_system, db_manager)
    
    def _show_query_interface(self, user: Dict, hybrid_system):
        """Show the main query interface"""
        
        st.markdown("#### 🎼 Describe your music mood")
        
        # Query input methods
        input_method = st.radio(
            "How would you like to search?",
            ["💬 Natural Language", "🎯 Quick Mood", "🎨 Creative Prompt"],
            horizontal=True
        )
        
        query = ""
        
        if input_method == "💬 Natural Language":
            query = self._show_natural_language_input()
        elif input_method == "🎯 Quick Mood":
            query = self._show_quick_mood_input()
        elif input_method == "🎨 Creative Prompt":
            query = self._show_creative_prompt_input()
        
        # Advanced options
        with st.expander("⚙️ Advanced Options"):
            max_results = st.slider("Number of recommendations", 3, 10, 5)
            use_rl = st.checkbox("Use AI personalization", 
                               value=True, 
                               help="Uses your personal AI model for better recommendations")
            exploration_mode = st.checkbox("Discovery mode", 
                                         help="Find new music outside your usual preferences")
        
        # Search button
        if st.button("🎵 Get Recommendations", type="primary", disabled=not query):
            self._process_recommendation_request(
                user, hybrid_system, query, max_results, use_rl, exploration_mode
            )
    
    def _show_natural_language_input(self) -> str:
        """Natural language query input"""
        
        # Example queries for inspiration
        examples = [
            "I need energetic music for my morning workout",
            "Something melancholic and introspective for a rainy day",
            "Upbeat tracks to get me pumped for a presentation", 
            "Chill ambient music for deep focus work",
            "Nostalgic songs that remind me of summer",
            "Electronic music perfect for late night coding",
            "Acoustic tracks for a cozy evening at home"
        ]
        
        selected_example = st.selectbox("💡 Or try an example:", [""] + examples)
        
        if selected_example:
            query = selected_example
        else:
            query = st.text_area(
                "Describe what you're looking for:",
                placeholder="e.g., I want something energetic but not too aggressive, maybe with good vocals...",
                height=100
            )
        
        return query
    
    def _show_quick_mood_input(self) -> str:
        """Quick mood-based input"""
        
        col1, col2 = st.columns(2)
        
        with col1:
            mood = st.selectbox("Current mood:", [
                "Happy & Energetic", "Calm & Peaceful", "Sad & Reflective",
                "Focused & Determined", "Nostalgic & Dreamy", "Angry & Intense",
                "Romantic & Loving", "Anxious & Restless", "Confident & Bold"
            ])
            
            activity = st.selectbox("What are you doing?", [
                "Working out", "Studying/Working", "Relaxing", "Commuting",
                "Cooking", "Cleaning", "Partying", "Dating", "Sleeping"
            ])
        
        with col2:
            energy_level = st.slider("Energy level you want:", 1, 10, 5)
            
            genre_preference = st.selectbox("Genre preference:", [
                "Any", "Rock", "Pop", "Electronic", "Hip-Hop", "Jazz",
                "Classical", "Country", "R&B", "Indie", "Alternative"
            ])
        
        # Build query from selections
        energy_desc = "high-energy" if energy_level > 7 else "moderate-energy" if energy_level > 4 else "low-energy"
        
        query = f"I'm feeling {mood.lower()} and I'm {activity.lower()}. I want {energy_desc} music"
        
        if genre_preference != "Any":
            query += f" in the {genre_preference.lower()} genre"
        
        query += f" with energy level {energy_level}/10."
        
        st.text_area("Generated query:", value=query, height=80, disabled=True)
        
        return query
    
    def _show_creative_prompt_input(self) -> str:
        """Creative prompt-based input"""
        
        st.markdown("🎨 **Let's get creative! Describe your ideal soundtrack:**")
        
        prompt_type = st.selectbox("Choose a creative angle:", [
            "🌅 Time & Place", "🎬 Movie Scene", "🌈 Color & Emotion", 
            "🌿 Nature & Elements", "📚 Literary Inspiration"
        ])
        
        if prompt_type == "🌅 Time & Place":
            query = st.text_input(
                "Describe a time and place:",
                placeholder="e.g., A foggy morning in a coffee shop in Paris..."
            )
        elif prompt_type == "🎬 Movie Scene":
            query = st.text_input(
                "Describe a movie scene:",
                placeholder="e.g., The hero walking away from an explosion in slow motion..."
            )
        elif prompt_type == "🌈 Color & Emotion":
            query = st.text_input(
                "Describe colors and emotions:",
                placeholder="e.g., Deep blue melancholy mixed with golden hope..."
            )
        elif prompt_type == "🌿 Nature & Elements":
            query = st.text_input(
                "Describe natural elements:",
                placeholder="e.g., The sound of rain on leaves mixed with distant thunder..."
            )
        elif prompt_type == "📚 Literary Inspiration":
            query = st.text_input(
                "Describe a literary mood:",
                placeholder="e.g., The introspective melancholy of a Murakami novel..."
            )
        
        if query:
            enhanced_query = f"Create a musical atmosphere that captures: {query}"
            st.text_area("Enhanced prompt:", value=enhanced_query, height=60, disabled=True)
            return enhanced_query
        
        return ""
    
    def _show_context_panel(self, user: Dict, hybrid_system):
        """Show context and user info panel"""
        
        # AI Status
        ai_status = hybrid_system.get_ai_status(user['id'])
        
        st.markdown("#### 🤖 Your AI Assistant")
        
        # AI capabilities
        if ai_status['rl_active']:
            st.success("✨ **Personalization Active**")
            st.write(f"• Trained on {ai_status['training_samples']} of your ratings")
            st.write(f"• {ai_status['accuracy']*100:.0f}% prediction accuracy")
            st.write("• Learning your unique taste")
        else:
            needed = 5 - ai_status['training_samples']
            st.info("🌱 **Learning Your Taste**")
            st.write(f"• Rate {needed} more tracks to unlock personalization")
            st.write("• Currently using general recommendations")
        
        # Quick stats
        st.markdown("#### 📊 Your Music Journey")
        
        # Get recent activity
        recent_stats = hybrid_system.db_manager.get_user_stats(user['id'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Queries", recent_stats.get('total_interactions', 0))
            st.metric("Ratings", recent_stats.get('total_feedback', 0))
        with col2:
            if recent_stats.get('average_rating', 0) > 0:
                st.metric("Avg Rating", f"{recent_stats['average_rating']:.1f}/5")
            st.metric("AI Level", f"{ai_status.get('training_samples', 0) * 2}%")
        
        # Recent discoveries
        if recent_stats.get('recent_high_rated'):
            st.markdown("#### 🎯 Recent Favorites")
            for track in recent_stats['recent_high_rated'][:3]:
                st.write(f"⭐ **{track['track_name']}** by {track['artist']}")
        
        # Listening insights
        insights = hybrid_system.get_learning_insights(user['id'])
        if insights.get('preferences'):
            st.markdown("#### 🧠 AI Insights")
            
            prefs = insights['preferences']
            if 'genres' in prefs and prefs['genres']:
                st.write(f"**Top genres:** {', '.join(prefs['genres'][:3])}")
            
            if 'moods' in prefs and prefs['moods']:
                st.write(f"**Preferred moods:** {', '.join(prefs['moods'][:2])}")
            
            # Personalization tips
            if ai_status['training_samples'] < 20:
                st.info("💡 **Tip:** Rate more diverse tracks to improve AI recommendations!")
    
    def _process_recommendation_request(self, user: Dict, hybrid_system, query: str, 
                                      max_results: int, use_rl: bool, exploration_mode: bool):
        """Process recommendation request"""
        
        with st.spinner("🎵 Your AI music curator is working..."):
            
            # Create request
            request = RecommendationRequest(
                user_id=user['id'],
                query=query,
                context={
                    'timestamp': datetime.now().isoformat(),
                    'exploration_mode': exploration_mode
                },
                max_results=max_results,
                use_rl_enhancement=use_rl
            )
            
            # Get recommendations
            try:
                response = asyncio.run(hybrid_system.get_recommendations(request))
                
                # Store in session
                st.session_state.current_recommendations = response
                st.session_state.current_query = query
                st.session_state.recommendation_timestamp = datetime.now()
                
                st.success(f"🎉 Found {len(response.tracks)} personalized recommendations!")
                st.rerun()
                
            except Exception as e:
                st.error(f"😞 Sorry, something went wrong: {str(e)}")
                st.write("Please try a different query or contact support if the problem persists.")
    
    def _show_recommendations(self, user: Dict, hybrid_system, db_manager):
        """Show the recommendations results"""
        
        recommendations = st.session_state.current_recommendations
        query = st.session_state.current_query
        
        st.markdown("---")
        
        # Results header
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"### 🎵 Recommendations for: *\"{query}\"*")
        
        with col2:
            # Hybrid confidence
            confidence = recommendations.hybrid_score * 100
            confidence_color = "🟢" if confidence > 80 else "🟡" if confidence > 60 else "🔴"
            st.metric("Confidence", f"{confidence_color} {confidence:.0f}%")
        
        with col3:
            # Processing time
            processing_time = recommendations.processing_time_ms
            st.metric("Response Time", f"{processing_time}ms")
        
        # AI reasoning
        if recommendations.reasoning:
            with st.expander("🤖 Why these recommendations?"):
                st.write(recommendations.reasoning)
                
                # Show LLM vs RL insights
                if recommendations.rl_insights.get('model_exists'):
                    st.markdown("**AI Enhancement Details:**")
                    st.write("• Used your personal listening history")
                    st.write("• Applied learned preferences")
                    st.write("• Balanced familiarity with discovery")
        
        # Recommendations display
        if not recommendations.tracks:
            st.warning("No tracks found. Try a different query or check your internet connection.")
            return
        
        # Display options
        display_mode = st.radio(
            "Display mode:",
            ["🎴 Detailed Cards", "📝 Compact List", "🎵 Audio Playlist"],
            horizontal=True
        )
        
        if display_mode == "🎴 Detailed Cards":
            self._show_detailed_cards(recommendations.tracks, user, hybrid_system, db_manager)
        elif display_mode == "📝 Compact List":
            self._show_compact_list(recommendations.tracks, user, hybrid_system)
        elif display_mode == "🎵 Audio Playlist":
            self._show_audio_playlist(recommendations.tracks, user, hybrid_system)
    
    def _show_detailed_cards(self, tracks: List[Dict], user: Dict, hybrid_system, db_manager):
        """Show detailed track cards"""
        
        for i, track in enumerate(tracks, 1):
            st.markdown(f"#### 🎵 Recommendation #{i}")
            
            # Track card with feedback
            feedback_result = self.track_card.render_card(
                track=track,
                user_id=user['id'],
                interaction_id=getattr(st.session_state, 'interaction_id', None),
                on_feedback=lambda feedback_data: self._handle_feedback(
                    feedback_data, hybrid_system
                ),
                show_rl_info=True
            )
            
            # Show enhancement details
            if track.get('rl_predicted_rating') or track.get('rl_bonus'):
                with st.expander("🔍 AI Enhancement Details"):
                    
                    if track.get('rl_predicted_rating'):
                        predicted = track['rl_predicted_rating']
                        confidence = track.get('rl_confidence', 0) * 100
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**AI Prediction:** {predicted:.1f}/5 stars")
                        with col2:
                            st.write(f"**Confidence:** {confidence:.0f}%")
                    
                    if track.get('rl_bonus'):
                        bonus = track['rl_bonus']
                        if bonus > 0:
                            st.success(f"🚀 Boosted by +{bonus:.1f} points based on your preferences")
                        elif bonus < 0:
                            st.info(f"⚖️ Lowered by {bonus:.1f} points (exploring new territory)")
                        
                    if track.get('diversity_penalty'):
                        penalty = track['diversity_penalty']
                        if penalty > 0:
                            st.warning(f"🔄 Diversity penalty: -{penalty:.1f} (similar to recent tracks)")
            
            st.markdown("---")
    
    def _show_compact_list(self, tracks: List[Dict], user: Dict, hybrid_system):
        """Show compact list view"""
        
        for i, track in enumerate(tracks, 1):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.write(f"**{i}. {track.get('name', 'Unknown')}**")
                st.caption(f"by {track.get('artist', 'Unknown')}")
            
            with col2:
                # Mini audio player
                if track.get('preview_url'):
                    self.audio_player.render_mini_player(track, f"mini_{i}")
                else:
                    st.write("🔇")
            
            with col3:
                # Score
                score = track.get('enhanced_score', track.get('ranking_score', 0))
                st.metric("Score", f"{score:.1f}")
            
            with col4:
                # Quick rating
                rating = st.selectbox(
                    "Rate",
                    [1, 2, 3, 4, 5],
                    index=2,
                    key=f"quick_rating_{i}",
                    label_visibility="collapsed"
                )
                
                if st.button("✓", key=f"quick_submit_{i}", help="Submit rating"):
                    feedback_data = {
                        'user_id': user['id'],
                        'track_id': track.get('id', f"track_{i}"),
                        'track_name': track.get('name', 'Unknown'),
                        'artist': track.get('artist', 'Unknown'),
                        'rating': rating,
                        'feedback_text': "Quick rating"
                    }
                    
                    result = self._handle_feedback(feedback_data, hybrid_system)
                    if result.get('success'):
                        st.success("✓")
    
    def _show_audio_playlist(self, tracks: List[Dict], user: Dict, hybrid_system):
        """Show playlist-style player"""
        
        # Filter playable tracks
        playable_tracks = [t for t in tracks if t.get('preview_url')]
        
        if not playable_tracks:
            st.warning("No audio previews available for these tracks.")
            return
        
        st.write(f"🎵 Playlist: {len(playable_tracks)} tracks with audio previews")
        
        # Playlist player
        player_result = self.audio_player.render_playlist_player(
            playable_tracks, 
            "recommendations_playlist"
        )
        
        if player_result:
            current_track = player_result['current_track']
            
            # Show info about current track
            st.markdown("#### Now Playing")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**{current_track.get('name')}**")
                st.write(f"by {current_track.get('artist')}")
                
                if current_track.get('lastfm_tags'):
                    tags = ', '.join(current_track['lastfm_tags'][:3])
                    st.caption(f"Tags: {tags}")
            
            with col2:
                # Rating for current track
                st.write("Rate this track:")
                rating = st.slider("Rating", 1, 5, 3, key="playlist_rating")
                
                if st.button("Submit Rating", key="playlist_submit"):
                    feedback_data = {
                        'user_id': user['id'],
                        'track_id': current_track.get('id'),
                        'track_name': current_track.get('name'),
                        'artist': current_track.get('artist'),
                        'rating': rating,
                        'feedback_text': "Playlist rating"
                    }
                    
                    self._handle_feedback(feedback_data, hybrid_system)
    
    def _handle_feedback(self, feedback_data: Dict, hybrid_system) -> Dict:
        """Handle user feedback"""
        
        try:
            # Process feedback through hybrid system
            result = asyncio.run(hybrid_system.process_feedback(
                user_id=feedback_data['user_id'],
                track_id=feedback_data['track_id'],
                rating=feedback_data['rating'],
                feedback_text=feedback_data.get('feedback_text', '')
            ))
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Usage function for main app
def show_home_page(user: Dict, hybrid_system, db_manager):
    """Show home page - called from main app"""
    home_page = HomePage()
    home_page.show_home_page(user, hybrid_system, db_manager)
