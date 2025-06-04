# Free Music Search Tool - Multiple Free APIs Integration
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from typing import Optional, Dict, List, Any
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
    # _audiodb_base: str = PrivateAttr(default="https://www.theaudiodb.com/api/v1/json/2")
    _genius_base: str = PrivateAttr(default="https://api.genius.com")
    _lastfm_key: str = PrivateAttr()
    _genius_token: str = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set API keys (optional - tools work without them but with limitations)
        lastfm_key = os.getenv('LASTFM_API_KEY', '')
        genius_token = os.getenv('GENIUS_ACCESS_TOKEN', 'fzR0MQSL3GhrNKdEEKteSXyOWzn0fvHn-yXr0fzZRXJHz5lj_FlrBe5bh8xxVL6n9Ce5s9SWfu4mi8wAnhj9cA')
        
        object.__setattr__(self, '_lastfm_key', lastfm_key)
        object.__setattr__(self, '_genius_token', genius_token)
        
        print(f"🎵 Free Music Search Tool Initialized")
        print(f"   🔧 Deezer API: ✅ (No key required)")
        print(f"   🔧 iTunes API: ✅ (No key required)")
        print(f"   🔧 MusicBrainz: ✅ (No key required)")
        print(f"   🔧 TheAudioDB: ✅ (No key required)")
        print(f"   🔧 Last.fm: {'✅' if lastfm_key else '⚠️  (Limited without key)'}")
        print(f"   🔧 Genius: {'✅' if genius_token else '⚠️  (Limited without key)'}")
    
    def _run(
        self, 
        search_params: str, 
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Search music using multiple free APIs"""
        
        print(f"\n🔍 Starting Free Music Search")
        print(f"="*50)
        
        try:
            # Parse search parameters
            if isinstance(search_params, str):
                try:
                    params = json.loads(search_params)
                except json.JSONDecodeError:
                    params = {"query": search_params}
            else:
                params = search_params
            
            search_query = params.get('query', '')
            if not search_query:
                # Generate query from context
                search_query = self._generate_search_query(params)
            
            print(f"🎯 Search Query: '{search_query}'")
            
            # Search multiple APIs in parallel
            all_tracks = []
            
            # 1. Deezer Search (Free, no key required)
            print(f"\n🟢 Searching Deezer...")
            deezer_tracks = self._search_deezer(search_query)
            all_tracks.extend(deezer_tracks)
            
            # 2. iTunes Search (Free, no key required)
            print(f"\n🟢 Searching iTunes...")
            itunes_tracks = self._search_itunes(search_query)
            all_tracks.extend(itunes_tracks)
            
            # 3. MusicBrainz Search (Free, no key required)
            print(f"\n🟢 Searching MusicBrainz...")
            mb_tracks = self._search_musicbrainz(search_query)
            all_tracks.extend(mb_tracks)
            
            # 4. TheAudioDB Search (Free, no key required)
            print(f"\n🟢 Searching TheAudioDB...")
            audiodb_tracks = self._search_audiodb(search_query)
            all_tracks.extend(audiodb_tracks)
            
            # 5. Last.fm Search (Free with key)
            if self._lastfm_key:
                print(f"\n🟢 Searching Last.fm...")
                lastfm_tracks = self._search_lastfm(search_query)
                all_tracks.extend(lastfm_tracks)
            
            # Remove duplicates and rank
            unique_tracks = self._deduplicate_and_rank(all_tracks)
            
            print(f"\n✅ Found {len(unique_tracks)} unique tracks from {len(all_tracks)} total results")
            
            return json.dumps({
                'tracks': unique_tracks[:30],  # Limit results
                'total_found': len(unique_tracks),
                'sources_used': ['deezer', 'itunes', 'musicbrainz', 'audiodb'] + (['lastfm'] if self._lastfm_key else []),
                'search_query': search_query
            })
            
        except Exception as e:
            print(f"❌ Error in free music search: {e}")
            return json.dumps({
                'error': str(e),
                'tracks': [],
                'total_found': 0
            })
    
    def _generate_search_query(self, params: Dict) -> str:
        """Generate search query from context parameters"""
        query_parts = []
        
        # Add mood descriptors
        if params.get('mood_descriptors'):
            query_parts.extend(params['mood_descriptors'][:2])
        
        # Add genre hints
        if params.get('genre_hints'):
            query_parts.extend(params['genre_hints'][:2])
        
        # Add activity context
        activity = params.get('activity_type', '')
        if 'workout' in activity.lower():
            query_parts.append('energetic')
        elif 'study' in activity.lower():
            query_parts.append('instrumental')
        elif 'chill' in activity.lower():
            query_parts.append('ambient')
        
        return ' '.join(query_parts) if query_parts else 'popular music'
    
    def _search_deezer(self, query: str) -> List[Dict]:
        """Search Deezer API (Free, no key required)"""
        try:
            url = f"{self._deezer_base}/search"
            params = {'q': query, 'limit': 25}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"   ❌ Deezer error: {response.status_code}")
                return []
            
            data = response.json()
            tracks = []
            
            for track in data.get('data', []):
                processed_track = {
                    'id': f"deezer_{track['id']}",
                    'name': track['title'],
                    'artist': track['artist']['name'],
                    'album': track['album']['title'],
                    'duration': track.get('duration', 0),
                    'preview_url': track.get('preview'),
                    'external_url': track.get('link'),
                    'source': 'deezer',
                    'features': {
                        'popularity': track.get('rank', 0),
                        'explicit': track.get('explicit_lyrics', False)
                    }
                }
                tracks.append(processed_track)
            
            print(f"   ✅ Deezer: {len(tracks)} tracks")
            return tracks
            
        except Exception as e:
            print(f"   ❌ Deezer error: {e}")
            return []
    
    def _search_itunes(self, query: str) -> List[Dict]:
        """Search iTunes API (Free, no key required)"""
        try:
            params = {
                'term': query,
                'media': 'music',
                'entity': 'song',
                'limit': 25
            }
            
            response = requests.get(self._itunes_base, params=params, timeout=10)
            if response.status_code != 200:
                print(f"   ❌ iTunes error: {response.status_code}")
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
                        'features': {
                            'genre': track.get('primaryGenreName'),
                            'price': track.get('trackPrice'),
                            'explicit': track.get('trackExplicitness') == 'explicit'
                        }
                    }
                    tracks.append(processed_track)
            
            print(f"   ✅ iTunes: {len(tracks)} tracks")
            return tracks
            
        except Exception as e:
            print(f"   ❌ iTunes error: {e}")
            return []
    
    def _search_musicbrainz(self, query: str) -> List[Dict]:
        """Search MusicBrainz API (Free, no key required)"""
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
                print(f"   ❌ MusicBrainz error: {response.status_code}")
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
                    'features': {
                        'mbid': recording['id'],
                        'score': recording.get('score', 0)
                    }
                }
                tracks.append(processed_track)
            
            print(f"   ✅ MusicBrainz: {len(tracks)} tracks")
            # Add delay to respect rate limits
            time.sleep(1)
            return tracks
            
        except Exception as e:
            print(f"   ❌ MusicBrainz error: {e}")
            return []
    
    def _search_audiodb(self, query: str) -> List[Dict]:
        """Search TheAudioDB API (Free, no key required)"""
        try:
            # TheAudioDB search by track name
            url = f"{self._audiodb_base}/searchtrack.php"
            params = {'s': query}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"   ❌ AudioDB error: {response.status_code}")
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
                        'features': {
                            'genre': track.get('strGenre'),
                            'year': track.get('intYear'),
                            'description': track.get('strDescriptionEN', '')[:100]
                        }
                    }
                    tracks.append(processed_track)
            
            print(f"   ✅ AudioDB: {len(tracks)} tracks")
            return tracks
            
        except Exception as e:
            print(f"   ❌ AudioDB error: {e}")
            return []
    
    def _search_lastfm(self, query: str) -> List[Dict]:
        """Search Last.fm API (Free with key)"""
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
                print(f"   ❌ Last.fm error: {response.status_code}")
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
                        'features': {
                            'listeners': track.get('listeners'),
                            'mbid': track.get('mbid')
                        }
                    }
                    tracks.append(processed_track)
            
            print(f"   ✅ Last.fm: {len(tracks)} tracks")
            return tracks
            
        except Exception as e:
            print(f"   ❌ Last.fm error: {e}")
            return []
    
    def _deduplicate_and_rank(self, tracks: List[Dict]) -> List[Dict]:
        """Remove duplicates and rank tracks by quality/relevance"""
        seen = set()
        unique_tracks = []
        
        for track in tracks:
            # Create a key for deduplication
            key = (track['name'].lower().strip(), track['artist'].lower().strip())
            
            if key not in seen:
                seen.add(key)
                
                # Calculate relevance score
                score = 0
                
                # Prefer tracks with preview URLs
                if track.get('preview_url'):
                    score += 10
                
                # Prefer tracks with external URLs
                if track.get('external_url'):
                    score += 5
                
                # Source preference (Deezer and iTunes have better metadata)
                source_scores = {
                    'deezer': 10,
                    'itunes': 9,
                    'lastfm': 7,
                    'audiodb': 6,
                    'musicbrainz': 5
                }
                score += source_scores.get(track['source'], 0)
                
                # Add popularity/ranking if available
                features = track.get('features', {})
                if 'popularity' in features:
                    score += features['popularity'] / 100
                if 'rank' in features:
                    score += features['rank'] / 1000
                
                track['relevance_score'] = score
                unique_tracks.append(track)
        
        # Sort by relevance score
        unique_tracks.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return unique_tracks
    
    async def _arun(
        self, 
        search_params: str, 
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, search_params, run_manager)

def test_free_music_search():
    """Test the free music search tool"""
    
    print(f"🧪 Testing Free Music Search Tool")
    print(f"="*60)
    
    # Test queries
    test_cases = [
        {
            "query": "chill electronic",
            "description": "Simple genre search"
        },
        {
            "mood_descriptors": ["energetic", "upbeat"],
            "genre_hints": ["rock", "electronic"],
            "activity_type": "workout",
            "description": "Complex context search"
        },
        {
            "query": "Beatles Yesterday",
            "description": "Specific song search"
        }
    ]
    
    try:
        tool = FreeMusicSearchTool()
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}: {test_case['description']}")
            print(f"{'='*40}")
            
            test_input = json.dumps(test_case)
            result = tool.invoke(test_input)
            data = json.loads(result)
            
            print(f"🎯 Search Query: {data.get('search_query', 'N/A')}")
            print(f"📊 Total Found: {data.get('total_found', 0)}")
            print(f"🔧 Sources Used: {', '.join(data.get('sources_used', []))}")
            
            tracks = data.get('tracks', [])
            if tracks:
                print(f"\n🎵 Top Results:")
                for j, track in enumerate(tracks[:3], 1):
                    preview = " 🎧" if track.get('preview_url') else ""
                    print(f"   {j}. {track['name']} by {track['artist']}{preview}")
                    print(f"      Source: {track['source']} | Score: {track.get('relevance_score', 0):.1f}")
                    if track.get('album'):
                        print(f"      Album: {track['album']}")
            else:
                print(f"❌ No tracks found")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")

# Setup instructions
def show_setup_instructions():
    """Show setup instructions for free APIs"""
    print(f"\n🔧 Setup Instructions for Free Music APIs:")
    print(f"="*60)
    print(f"")
    print(f"✅ NO SETUP REQUIRED:")
    print(f"   • Deezer API - Works immediately")
    print(f"   • iTunes API - Works immediately") 
    print(f"   • MusicBrainz API - Works immediately")
    print(f"   • TheAudioDB API - Works immediately")
    print(f"")
    print(f"🔑 OPTIONAL API KEYS (for better results):")
    print(f"   • Last.fm API Key:")
    print(f"     1. Go to: https://www.last.fm/api/account/create")
    print(f"     2. Create account and get API key")
    print(f"     3. Add to .env: LASTFM_API_KEY=your_key")
    print(f"")
    print(f"   • Genius API Token:")
    print(f"     1. Go to: https://genius.com/api-clients")
    print(f"     2. Create app and get access token")
    print(f"     3. Add to .env: GENIUS_ACCESS_TOKEN=your_token")
    print(f"")
    print(f"💡 The tool works great even without any API keys!")

if __name__ == "__main__":
    print(f"🎵 Free Music Search Tool - Spotify Alternative")
    print(f"="*70)
    
    # Show setup instructions
    show_setup_instructions()
    
    # Run tests
    test_free_music_search()
    
    print(f"\n✅ Free music search testing completed!")
    print(f"🚀 This tool replaces Spotify API with multiple free alternatives!")