from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from typing import Optional, Dict, List
import json
import requests
import asyncio
import time
from dotenv import load_dotenv
import os
from pydantic import PrivateAttr

load_dotenv()

class FreeMusicSearchTool(BaseTool):
    name: str = "free_music_search"
    description: str = "Search for music using multiple free APIs (Deezer, iTunes, Last.fm, MusicBrainz)"
    _deezer_base: str = PrivateAttr(default="https://api.deezer.com")
    _itunes_base: str = PrivateAttr(default="https://itunes.apple.com/search")
    _lastfm_base: str = PrivateAttr(default="http://ws.audioscrobbler.com/2.0/")
    _musicbrainz_base: str = PrivateAttr(default="https://musicbrainz.org/ws/2")
    _audiodb_base: str = PrivateAttr(default="https://www.theaudiodb.com/api/v1/json/2")
    _lastfm_key: str = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        lastfm_key = os.getenv('LASTFM_API_KEY', '')
        object.__setattr__(self, '_lastfm_key', lastfm_key)
        
        print(f"🎵 Free Music Search Tool Initialized")
        print(f"Deezer API: (No key required)")
        print(f"iTunes API: (No key required)")
        print(f"MusicBrainz: (No key required)")
        print(f"TheAudioDB: (No key required)")
        print(f"Last.fm: {'OK' if lastfm_key else 'Not OK  (Limited without key)'}")
    
    def _run(
        self, 
        search_params: str, 
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Search music using multiple free APIs"""
        print(f"\nStarting Free Music Search")
        print(f"="*50)
        
        try:
            if isinstance(search_params, str):
                try:
                    params = json.loads(search_params)
                except json.JSONDecodeError:
                    params = {"query": search_params}
            else:
                params = search_params
            
            search_query = params.get('query', '')
            if not search_query:
                search_query = self._generate_search_query(params)
            
            print(f"Search Query: '{search_query}'")
            all_tracks = []
            
            print(f"\nSearching Deezer...")
            deezer_tracks = self._search_deezer(search_query)
            all_tracks.extend(deezer_tracks)
            
            print(f"\nSearching iTunes...")
            itunes_tracks = self._search_itunes(search_query)
            all_tracks.extend(itunes_tracks)
            
            print(f"\nSearching MusicBrainz...")
            mb_tracks = self._search_musicbrainz(search_query)
            all_tracks.extend(mb_tracks)
            
            print(f"\nSearching TheAudioDB...")
            audiodb_tracks = self._search_audiodb(search_query)
            all_tracks.extend(audiodb_tracks)
            
            if self._lastfm_key:
                print(f"\nSearching Last.fm...")
                lastfm_tracks = self._search_lastfm(search_query)
                all_tracks.extend(lastfm_tracks)
            
            unique_tracks = self._deduplicate_and_rank(all_tracks)
            
            print(f"\nFound {len(unique_tracks)} unique tracks from {len(all_tracks)} total results")
            
            return json.dumps({
                'tracks': unique_tracks[:30],  # Limit results
                'total_found': len(unique_tracks),
                'sources_used': ['deezer', 'itunes', 'musicbrainz', 'audiodb'] + (['lastfm'] if self._lastfm_key else []),
                'search_query': search_query
            })
            
        except Exception as e:
            print(f"Error in free music search: {e}")
            return json.dumps({
                'error': str(e),
                'tracks': [],
                'total_found': 0
            })
    
    def _generate_search_query(self, params: Dict) -> str:
        query_parts = []
        if params.get('mood_descriptors'):
            query_parts.extend(params['mood_descriptors'][:2])
        
        if params.get('genre_hints'):
            query_parts.extend(params['genre_hints'][:2])
        
        activity = params.get('activity_type', '')
        if 'workout' in activity.lower():
            query_parts.append('energetic')
        elif 'study' in activity.lower():
            query_parts.append('instrumental')
        elif 'chill' in activity.lower():
            query_parts.append('ambient')
        
        return ' '.join(query_parts) if query_parts else 'popular music'
    
    def _search_deezer(self, query: str) -> List[Dict]:
        try:
            url = f"{self._deezer_base}/search"
            params = {'q': query, 'limit': 25}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"Deezer error: {response.status_code}")
                return []
            
            data = response.json()
            tracks = []
            
            for track in data.get('data', []):
                processed_track = {
                    'id': f"deezer_{track['id']}",
                    'name': track['title'],
                    'artist': track['artist']['name'],
                    'album': track['album']['title'],
                    'duration': track.get('duration', 0) * 1000,  # Convert to ms
                    'preview_url': track.get('preview'),
                    'external_url': track.get('link'),
                    'source': 'deezer',
                    'popularity': track.get('rank', 0),
                    'explicit': track.get('explicit_lyrics', False),
                    'estimated_features': self._estimate_audio_features(track)
                }
                tracks.append(processed_track)
            
            print(f"Deezer: {len(tracks)} tracks")
            return tracks
            
        except Exception as e:
            print(f"Deezer error: {e}")
            return []
    
    def _search_itunes(self, query: str) -> List[Dict]:
        try:
            params = {
                'term': query,
                'media': 'music',
                'entity': 'song',
                'limit': 25
            }
            
            response = requests.get(self._itunes_base, params=params, timeout=10)
            if response.status_code != 200:
                print(f"iTunes error: {response.status_code}")
                return []
            
            data = response.json()
            tracks = []
            
            for track in data.get('results', []):
                if track.get('kind') == 'song':
                    processed_track = {
                        'id': f"itunes_{track['trackId']}",
                        'name': track['trackName'],
                        'artist': track['artistName'],
                        'album': track.get('collectionName', ''),
                        'duration': track.get('trackTimeMillis', 0),
                        'preview_url': track.get('previewUrl'),
                        'external_url': track.get('trackViewUrl'),
                        'source': 'itunes',
                        'popularity': 0,  # iTunes doesn't provide popularity
                        'explicit': track.get('trackExplicitness') == 'explicit',
                        'genre': track.get('primaryGenreName'),
                        'estimated_features': self._estimate_audio_features(track, source='itunes')
                    }
                    tracks.append(processed_track)
            
            print(f"iTunes: {len(tracks)} tracks")
            return tracks
            
        except Exception as e:
            print(f"iTunes error: {e}")
            return []
    
    def _search_musicbrainz(self, query: str) -> List[Dict]:
        try:
            url = f"{self._musicbrainz_base}/recording"
            params = {
                'query': query,
                'fmt': 'json',
                'limit': 20
            }
            
            headers = {'User-Agent': 'MusicRecommendationAI/1.0'}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"MusicBrainz error: {response.status_code}")
                return []
            
            data = response.json()
            tracks = []
            
            for recording in data.get('recordings', []):
                artist_name = 'Unknown Artist'
                if recording.get('artist-credit'):
                    artist_name = recording['artist-credit'][0]['name']
                
                release_info = recording.get('releases', [{}])[0] if recording.get('releases') else {}
                
                processed_track = {
                    'id': f"mb_{recording['id']}",
                    'name': recording['title'],
                    'artist': artist_name,
                    'album': release_info.get('title', ''),
                    'duration': recording.get('length', 0),
                    'source': 'musicbrainz',
                    'popularity': recording.get('score', 50),  # Use MusicBrainz score
                    'mbid': recording['id'],
                    'estimated_features': self._estimate_audio_features(recording, source='musicbrainz')
                }
                tracks.append(processed_track)
            
            print(f"MusicBrainz: {len(tracks)} tracks")
            time.sleep(1)
            return tracks
            
        except Exception as e:
            print(f"MusicBrainz error: {e}")
            return []
    
    def _search_audiodb(self, query: str) -> List[Dict]:
        try:
            url = f"{self._audiodb_base}/searchtrack.php"
            params = {'s': query}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"AudioDB error: {response.status_code}")
                return []
            
            data = response.json()
            tracks = []
            
            if data.get('track'):
                for track in data['track']:
                    processed_track = {
                        'id': f"audiodb_{track['idTrack']}",
                        'name': track['strTrack'],
                        'artist': track['strArtist'],
                        'album': track.get('strAlbum', ''),
                        'source': 'audiodb',
                        'popularity': 0,
                        'genre': track.get('strGenre'),
                        'year': track.get('intYear'),
                        'description': track.get('strDescriptionEN', '')[:100],
                        'estimated_features': self._estimate_audio_features(track, source='audiodb')
                    }
                    tracks.append(processed_track)
            
            print(f"AudioDB: {len(tracks)} tracks")
            return tracks
            
        except Exception as e:
            print(f"AudioDB error: {e}")
            return []
    
    def _search_lastfm(self, query: str) -> List[Dict]:
        if not self._lastfm_key:
            return []
        
        try:
            url = self._lastfm_base
            params = {
                'method': 'track.search',
                'track': query,
                'api_key': self._lastfm_key,
                'format': 'json',
                'limit': 20
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"Last.fm error: {response.status_code}")
                return []
            
            data = response.json()
            tracks = []
            
            if 'results' in data and 'trackmatches' in data['results']:
                for track in data['results']['trackmatches']['track']:
                    processed_track = {
                        'id': f"lastfm_{track['mbid'] if track.get('mbid') else hash(track['name'] + track['artist'])}",
                        'name': track['name'],
                        'artist': track['artist'],
                        'source': 'lastfm',
                        'external_url': track.get('url'),
                        'popularity': int(track.get('listeners', 0)) // 1000,  # Convert to 0-100 scale
                        'listeners': track.get('listeners'),
                        'mbid': track.get('mbid'),
                        'estimated_features': self._estimate_audio_features(track, source='lastfm')
                    }
                    tracks.append(processed_track)
            
            print(f"Last.fm: {len(tracks)} tracks")
            return tracks
            
        except Exception as e:
            print(f"Last.fm error: {e}")
            return []
    
    def _estimate_audio_features(self, track_data: Dict, source: str = 'unknown') -> Dict:
        features = {
            'energy': 0.5,
            'valence': 0.5,
            'danceability': 0.5,
            'acousticness': 0.3,
            'instrumentalness': 0.1,
            'tempo': 120,
            'loudness': -8.0,
            'estimated': True
        }
        
        genre = track_data.get('genre', '').lower() if isinstance(track_data.get('genre'), str) else ''
        
        if any(word in genre for word in ['rock', 'metal', 'punk']):
            features.update({'energy': 0.8, 'loudness': -5.0, 'tempo': 140})
        elif any(word in genre for word in ['electronic', 'dance', 'edm']):
            features.update({'energy': 0.9, 'danceability': 0.9, 'tempo': 128})
        elif any(word in genre for word in ['classical', 'instrumental']):
            features.update({'acousticness': 0.9, 'instrumentalness': 0.8, 'energy': 0.3})
        elif any(word in genre for word in ['jazz', 'blues']):
            features.update({'acousticness': 0.7, 'energy': 0.4, 'valence': 0.4})
        elif any(word in genre for word in ['pop', 'mainstream']):
            features.update({'valence': 0.7, 'danceability': 0.7, 'energy': 0.6})
        elif any(word in genre for word in ['ambient', 'chill']):
            features.update({'energy': 0.2, 'valence': 0.6, 'acousticness': 0.6})
        
        popularity = track_data.get('popularity', 50)
        if popularity > 70:
            features['valence'] = min(0.9, features['valence'] + 0.2)
            features['danceability'] = min(0.9, features['danceability'] + 0.1)
        
        return features
    
    def _deduplicate_and_rank(self, tracks: List[Dict]) -> List[Dict]:
        seen = set()
        unique_tracks = []
        
        for track in tracks:
            key = (track['name'].lower().strip(), track['artist'].lower().strip())
            
            if key not in seen:
                seen.add(key)

                score = 0
                if track.get('preview_url'):
                    score += 10
            
                if track.get('external_url'):
                    score += 5
                source_scores = {
                    'deezer': 10,
                    'itunes': 9,
                    'lastfm': 7,
                    'audiodb': 6,
                    'musicbrainz': 5
                }
                score += source_scores.get(track['source'], 0)
                popularity = track.get('popularity', 0)
                score += popularity / 10
                
                track['relevance_score'] = score
                unique_tracks.append(track)
    
        unique_tracks.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return unique_tracks
    
    async def _arun(
        self, 
        search_params: str, 
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, search_params, run_manager)

