import streamlit as st

class AudioPlayer:
    def __init__(self):
        self.player_id = 0
    
    def render_player(self, track: dict, key: str = None) -> bool:
        """Render audio player for a track"""
        
        if not key:
            key = f"player_{self.player_id}"
            self.player_id += 1
        
        preview_url = track.get('preview_url')
        track_name = track.get('name', 'Unknown Track')
        artist = track.get('artist', 'Unknown Artist')
        
        if not preview_url:
            st.write("🔇 No audio preview available")
            return False
        
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            st.markdown(f"""
            <div style="
                background: linear-gradient(45deg, #667eea, #764ba2);
                width: 60px;
                height: 60px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 12px;
                text-align: center;
            ">
                🎵
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="padding: 8px 0;">
                <div style="font-weight: bold; font-size: 14px; margin-bottom: 4px;">
                    {track_name[:30]}{'...' if len(track_name) > 30 else ''}
                </div>
                <div style="color: #888; font-size: 12px;">
                    {artist[:25]}{'...' if len(artist) > 25 else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.audio(preview_url, format='audio/mp3')
        
        with col3:
            if st.button("🔗", key=f"link_{key}", help="Open external link"):
                external_url = track.get('external_url')
                if external_url:
                    st.write(f"[Open in {track.get('source', 'browser')}]({external_url})")
                else:
                    st.info("No external link available")
        
        return True
    
    def render_mini_player(self, track: dict, key: str = None) -> bool:
        if not key:
            key = f"mini_{self.player_id}"
            self.player_id += 1
        
        preview_url = track.get('preview_url')
        if not preview_url:
            st.caption("🔇 No preview")
            return False
        
        with st.container():
            st.audio(preview_url, format='audio/mp3')
        
        return True
    
    def render_playlist_player(self, tracks: list, key: str = None) -> dict:
        if not key:
            key = f"playlist_{self.player_id}"
            self.player_id += 1
        
        playable_tracks = [t for t in tracks if t.get('preview_url')]
        
        if not playable_tracks:
            st.info("No audio previews available for these tracks")
            return {}
        
        track_options = [
            f"{t.get('name', 'Unknown')} - {t.get('artist', 'Unknown')}" 
            for t in playable_tracks
        ]
        
        selected_idx = st.selectbox(
            "Select track to play:",
            range(len(track_options)),
            format_func=lambda x: track_options[x],
            key=f"selector_{key}"
        )
        
        selected_track = playable_tracks[selected_idx]
        self.render_player(selected_track, f"selected_{key}")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("⏮️ Previous", key=f"prev_{key}"):
                if selected_idx > 0:
                    st.session_state[f"selector_{key}"] = selected_idx - 1
                    st.rerun()
        
        with col2:
            st.write(f"{selected_idx + 1} of {len(playable_tracks)}")
        
        with col3:
            if st.button("⏭️ Next", key=f"next_{key}"):
                if selected_idx < len(playable_tracks) - 1:
                    st.session_state[f"selector_{key}"] = selected_idx + 1
                    st.rerun()
        
        return {
            'current_track': selected_track,
            'track_index': selected_idx,
            'total_tracks': len(playable_tracks)
        }

