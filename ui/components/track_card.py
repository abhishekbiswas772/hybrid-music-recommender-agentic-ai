import time
import streamlit as st
from typing import Dict, Optional, Callable


class TrackCard:
    def __init__(self, audio_player):
        self.audio_player = audio_player
    
    def render_card(self, track: Dict, user_id: int, interaction_id: Optional[int] = None, 
                   on_feedback: Optional[Callable] = None, show_rl_info: bool = True) -> Dict:
        with st.container():
            st.markdown(f"""
            <div style="
                background: rgba(255, 255, 255, 0.1);
                padding: 1.5rem;
                border-radius: 15px;
                margin: 1rem 0;
                backdrop-filter: blur(15px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            ">
            """, unsafe_allow_html=True)
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### 🎵 {track.get('name', 'Unknown Track')}")
                st.markdown(f"**Artist:** {track.get('artist', 'Unknown Artist')}")
                if track.get('album'):
                    st.markdown(f"**Album:** {track.get('album')}")
            
            with col2:
                source = track.get('source', 'unknown').title()
                st.markdown(f"**Source:** {source}")
                
                base_score = track.get('ranking_score', 0)
                st.markdown(f"**Score:** {base_score:.2f}")
            
            tab1, tab2, tab3 = st.tabs(["🎵 Audio", "📊 Details", "🤖 AI Insights"])
            
            with tab1:
                self.audio_player.render_player(track, f"card_{track.get('id', 'unknown')}")
                if track.get('estimated_features'):
                    self._render_audio_features(track['estimated_features'])
            
            with tab2:
                self._render_track_details(track)
            
            with tab3:
                if show_rl_info:
                    self._render_ai_insights(track)
            
            feedback_result = {}
            if interaction_id and user_id:
                feedback_result = self._render_feedback_section(
                    track, user_id, interaction_id, on_feedback
                )
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            return feedback_result
    
    def _render_audio_features(self, features: Dict):
        st.markdown("#### 🎚️ Audio Characteristics")
        feature_names = {
            'energy': 'Energy',
            'valence': 'Positivity',
            'danceability': 'Danceability',
            'acousticness': 'Acoustic',
            'instrumentalness': 'Instrumental'
        }
        
        for feature, display_name in feature_names.items():
            value = features.get(feature, 0.5)
            percentage = int(value * 100)
            bar_color = self._get_feature_color(feature, value)
            st.markdown(f"""
            <div style="margin: 8px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold;">{display_name}</span>
                    <span>{percentage}%</span>
                </div>
                <div style="
                    background: rgba(255,255,255,0.2);
                    border-radius: 10px;
                    height: 8px;
                    overflow: hidden;
                ">
                    <div style="
                        background: {bar_color};
                        height: 100%;
                        width: {percentage}%;
                        border-radius: 10px;
                        transition: width 0.3s ease;
                    "></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            tempo = features.get('tempo', 120)
            st.metric("Tempo", f"{tempo:.0f} BPM")
        with col2:
            loudness = features.get('loudness', -8)
            st.metric("Loudness", f"{loudness:.1f} dB")
    
    def _render_track_details(self, track: Dict):
        col1, col2 = st.columns(2)
        
        with col1:
            if track.get('duration'):
                duration_mins = track['duration'] // 60000
                duration_secs = (track['duration'] % 60000) // 1000
                st.metric("Duration", f"{duration_mins}:{duration_secs:02d}")
            
            if track.get('popularity') is not None:
                st.metric("Popularity", f"{track['popularity']}/100")
        
        with col2:
            if track.get('year'):
                st.metric("Year", track['year'])
            
            if track.get('explicit') is not None:
                explicit_text = "Yes" if track['explicit'] else "No"
                st.metric("Explicit", explicit_text)
        
        if track.get('lastfm_tags'):
            st.markdown("#### 🏷️ Tags")
            tags_html = "".join([
                f'<span style="background: linear-gradient(45deg, #ff6b6b, #feca57); color: white; padding: 0.3rem 0.8rem; border-radius: 15px; margin: 0.2rem; display: inline-block; font-size: 0.8rem;">{tag}</span>'
                for tag in track['lastfm_tags'][:6]
            ])
            st.markdown(tags_html, unsafe_allow_html=True)
        
        if track.get('external_url'):
            st.markdown(f"🔗 [Listen on {track.get('source', 'platform').title()}]({track['external_url']})")
        
        if track.get('similar_tracks'):
            with st.expander("🔄 Similar Tracks"):
                for similar in track['similar_tracks'][:3]:
                    match_score = similar.get('match', 0) * 100
                    st.write(f"• **{similar.get('name')}** by {similar.get('artist')} ({match_score:.0f}% match)")
    
    def _render_ai_insights(self, track: Dict):
        if track.get('rl_predicted_rating'):
            predicted = track['rl_predicted_rating']
            confidence = track.get('rl_confidence', 0) * 100
            
            st.markdown("#### 🤖 AI Prediction")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Predicted Rating", f"{predicted:.1f}/5")
            with col2:
                st.metric("Confidence", f"{confidence:.0f}%")
        
        if track.get('rl_bonus') is not None:
            bonus = track['rl_bonus']
            bonus_type = "Boost" if bonus > 0 else "Penalty" if bonus < 0 else "Neutral"
            bonus_color = "green" if bonus > 0 else "red" if bonus < 0 else "gray"
            
            st.markdown(f"""
            <div style="
                background: rgba(255,255,255,0.1);
                padding: 1rem;
                border-radius: 10px;
                border-left: 4px solid {bonus_color};
                margin: 1rem 0;
            ">
                <strong>Personalization {bonus_type}:</strong> {bonus:+.2f} points<br>
                <small>Based on your listening history and preferences</small>
            </div>
            """, unsafe_allow_html=True)
        
        if track.get('feature_contributions'):
            st.markdown("#### 📊 Why This Track?")
            contributions = track['feature_contributions']
            
            for feature, contribution in sorted(contributions.items(), 
                                              key=lambda x: abs(x[1]), reverse=True)[:5]:
                contribution_type = "positive" if contribution > 0 else "negative"
                color = "green" if contribution > 0 else "red"
                
                st.markdown(f"""
                <div style="margin: 4px 0;">
                    <span style="color: {color};">{'▲' if contribution > 0 else '▼'}</span>
                    <strong>{feature.replace('_', ' ').title()}:</strong> 
                    {contribution:+.2f}
                </div>
                """, unsafe_allow_html=True)
    
    def _render_feedback_section(self, track: Dict, user_id: int, interaction_id: int, 
                                on_feedback: Optional[Callable]) -> Dict:
        track_id = track.get('id', f"unknown_{hash(track.get('name', '') + track.get('artist', ''))}")
        
        st.markdown("---")
        st.markdown("#### ⭐ Rate This Track")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            rating = st.slider(
                "How much do you like this track?",
                min_value=1,
                max_value=5,
                value=3,
                key=f"rating_{track_id}_{interaction_id}",
                help="1 = Hate it, 5 = Love it"
            )
            
            rating_descriptions = {
                1: "😞 Not for me",
                2: "😐 It's okay",
                3: "🙂 I like it",
                4: "😊 Really good!",
                5: "🤩 Amazing!"
            }
            st.caption(rating_descriptions.get(rating, ""))
        
        with col2:
            stars = "⭐" * rating + "☆" * (5 - rating)
            st.markdown(f"<div style='font-size: 2rem; text-align: center;'>{stars}</div>", 
                       unsafe_allow_html=True)
        
        # Feedback text
        feedback_text = st.text_area(
            "Tell us why (optional):",
            placeholder="What did you like or dislike about this track?",
            key=f"feedback_{track_id}_{interaction_id}",
            max_chars=500
        )
        
        # Feedback categories
        st.markdown("**Quick feedback:**")
        feedback_categories = {
            "🎵 Great melody": f"melody_{track_id}",
            "🎤 Love the vocals": f"vocals_{track_id}",
            "💃 Makes me dance": f"dance_{track_id}",
            "😌 Perfect mood": f"mood_{track_id}",
            "🔊 Too loud": f"loud_{track_id}",
            "😴 Too boring": f"boring_{track_id}",
            "❌ Wrong genre": f"genre_{track_id}"
        }
        
        selected_categories = []
        cols = st.columns(3)
        for i, (category, key) in enumerate(feedback_categories.items()):
            with cols[i % 3]:
                if st.checkbox(category, key=key):
                    selected_categories.append(category)
        
        if st.button(f"Submit Rating", key=f"submit_{track_id}_{interaction_id}", type="primary"):
            feedback_data = {
                'user_id': user_id,
                'interaction_id': interaction_id,
                'track_id': track_id,
                'track_name': track.get('name', 'Unknown'),
                'artist': track.get('artist', 'Unknown'),
                'album': track.get('album', ''),
                'rating': rating,
                'predicted_rating': track.get('rl_predicted_rating'),
                'rl_confidence': track.get('rl_confidence'),
                'feedback_text': feedback_text,
                'feedback_categories': selected_categories,
                'track_features': track.get('estimated_features', {}),
                'track_tags': track.get('lastfm_tags', []),
                'source': track.get('source'),
                'popularity': track.get('popularity'),
                'relevance_score': track.get('relevance_score'),
                'timestamp': time.time()
            }
    
            if on_feedback:
                result = on_feedback(feedback_data)
                
                if result.get('success'):
                    st.success("🎉 Thank you for your feedback!")
                    if result.get('model_updated'):
                        st.info("🧠 Your AI model has been updated with this feedback!")
                    
                    if 'message' in result:
                        st.info(result['message'])
                else:
                    st.error("Failed to save feedback. Please try again.")
            
            return feedback_data
        
        return {}
    
    def _get_feature_color(self, feature: str, value: float) -> str:
        if feature in ['energy', 'danceability']:
            if value > 0.7:
                return "linear-gradient(90deg, #ff6b6b, #ff8e53)"
            elif value > 0.4:
                return "linear-gradient(90deg, #feca57, #ff9ff3)"
            else:
                return "linear-gradient(90deg, #54a0ff, #5f27cd)"
        
        elif feature == 'valence':
            if value > 0.6:
                return "linear-gradient(90deg, #feca57, #ff9ff3)"
            else:
                return "linear-gradient(90deg, #54a0ff, #5f27cd)"
        
        elif feature in ['acousticness', 'instrumentalness']:
            return "linear-gradient(90deg, #26de81, #20bf6b)"
        
        else:
            return "linear-gradient(90deg, #667eea, #764ba2)"

