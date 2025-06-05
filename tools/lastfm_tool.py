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
import traceback

load_dotenv()


class LastFmEnrichmentTool(BaseTool):
    name: str = "lastfm_enrichment"
    description: str = "Enrich tracks with semantic tags and similar track data from Last.fm"
    
    _api_key: str = PrivateAttr()
    _base_url: str = PrivateAttr(default="http://ws.audioscrobbler.com/2.0/")
    
    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(**kwargs)
        key = api_key or os.getenv('LASTFM_API_KEY') or "d049d35548ed162784a327cf9ed67546"
        object.__setattr__(self, '_api_key', key)
        object.__setattr__(self, '_base_url', "http://ws.audioscrobbler.com/2.0/")
        print(f"Last.fm Tool Initialized with key: {key[:12]}...{key[-4:]}")
    
    @property
    def api_key(self):
        return self._api_key
    
    @property
    def base_url(self):
        return self._base_url
    
    def _run(
        self, 
        track_data: str, 
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Enrich tracks with Last.fm data"""
        
        try:
            if isinstance(track_data, str):
                data = json.loads(track_data)
            else:
                data = track_data
            
            if isinstance(data, list):
                tracks = data
            elif isinstance(data, dict):
                if 'tracks' in data:
                    tracks = data['tracks']
                else:
                    tracks = [data]
            else:
                return json.dumps({'error': 'Invalid input format', 'enriched_tracks': []})
            
            enriched_tracks = []
            
            print(f"Enriching {len(tracks[:10])} tracks with Last.fm...")
            for i, track in enumerate(tracks[:10]):
                try:
                    artist = track.get('artist', '')
                    name = track.get('name', '')
                    
                    if not artist or not name:
                        enriched_tracks.append(track)
                        continue
                    
                    tags = self._get_track_tags(artist, name)
                    similar = self._get_similar_tracks(artist, name)
                    enriched_track = track.copy()
                    enriched_track['lastfm_tags'] = tags
                    enriched_track['similar_tracks'] = similar
                    enriched_track['enriched'] = True
                    enriched_tracks.append(enriched_track)
                    if i < len(tracks[:10]) - 1:
                        time.sleep(0.2)
                    
                except Exception as e:
                    print(f"Error enriching track: {e}")
                    enriched_tracks.append(track)
                    continue
            
            print(f"Successfully enriched {len(enriched_tracks)} tracks")
            return json.dumps({
                'enriched_tracks': enriched_tracks,
                'total_enriched': len(enriched_tracks),
                'lastfm_used': True
            })
        except Exception as e:
            print(f"Last.fm enrichment error: {e}")
            return json.dumps({
                'error': str(e),
                'enriched_tracks': [],
                'lastfm_used': False
            })
    
    def _get_track_tags(self, artist: str, track: str) -> List[str]:
        params = {
            'method': 'track.gettoptags',
            'artist': artist,
            'track': track,
            'api_key': self.api_key,
            'format': 'json'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code != 200:
                return []
            
            data = response.json()
            if 'toptags' in data and 'tag' in data['toptags']:
                tags_data = data['toptags']['tag']
                if isinstance(tags_data, list):
                    return [tag['name'] for tag in tags_data[:8] if 'name' in tag]
                elif isinstance(tags_data, dict) and 'name' in tags_data:
                    return [tags_data['name']]
            
        except Exception as e:
            print(f"Error getting tags: {e}")
        
        return []
    
    def _get_similar_tracks(self, artist: str, track: str) -> List[Dict]:
        params = {
            'method': 'track.getsimilar',
            'artist': artist,
            'track': track,
            'api_key': self.api_key,
            'format': 'json',
            'limit': 5
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code != 200:
                return []
            
            data = response.json()
            if 'similartracks' in data and 'track' in data['similartracks']:
                similar_data = data['similartracks']['track']
                if isinstance(similar_data, list):
                    return [
                        {
                            'name': track_item['name'],
                            'artist': track_item['artist']['name'] if isinstance(track_item['artist'], dict) else str(track_item['artist']),
                            'match': float(track_item.get('match', 0)),
                            'url': track_item.get('url', '')
                        }
                        for track_item in similar_data
                        if 'name' in track_item and 'artist' in track_item
                    ]
                elif isinstance(similar_data, dict) and 'name' in similar_data:
                    return [{
                        'name': similar_data['name'],
                        'artist': similar_data['artist']['name'] if isinstance(similar_data['artist'], dict) else str(similar_data['artist']),
                        'match': float(similar_data.get('match', 0)),
                        'url': similar_data.get('url', '')
                    }]
            
        except Exception as e:
            print(f"Error getting similar tracks: {e}")
        
        return []
    
    async def _arun(
        self, 
        track_data: str, 
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, track_data, run_manager)

