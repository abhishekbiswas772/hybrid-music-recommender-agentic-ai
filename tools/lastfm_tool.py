# Verbose Last.fm Tool - Detailed Logging
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
        
        print(f"Last.fm Tool Initialized:")
        print(f"API Key: {key[:12]}...{key[-4:] if len(key) > 16 else key}")
        print(f"Base URL: {self.base_url}")
    
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
        print(f"\n{'='*60}")
        print(f"Starting Last.fm Enrichment Process")
        print(f"{'='*60}")
        
        try:
            print(f"📥 Input received: {track_data[:100]}{'...' if len(track_data) > 100 else ''}")
            
            if isinstance(track_data, str):
                try:
                    data = json.loads(track_data)
                    print(f"Successfully parsed JSON input")
                except json.JSONDecodeError as e:
                    print(f"JSON parsing failed: {e}")
                    return json.dumps({'error': 'Invalid JSON input', 'enriched_tracks': []})
            else:
                data = track_data
                print(f"Input is already parsed data")
        
            if isinstance(data, list):
                tracks = data
                print(f"Input format: List of {len(tracks)} tracks")
            elif isinstance(data, dict):
                if 'tracks' in data:
                    tracks = data['tracks']
                    print(f"Input format: Dict with 'tracks' key containing {len(tracks)} tracks")
                else:
                    tracks = [data]
                    print(f"Input format: Single track dict")
            else:
                print(f"Invalid input format: {type(data)}")
                return json.dumps({'error': 'Invalid input format', 'enriched_tracks': []})
            
            enriched_tracks = []
            successful_enrichments = 0
            failed_enrichments = 0
            
            print(f"\nStarting enrichment of {len(tracks[:10])} tracks...")
            print(f"Rate limiting: 200ms delay between API calls")
            
            for i, track in enumerate(tracks[:10]):  
                print(f"\n Processing Track {i+1}/{min(len(tracks), 10)}:")
                print(f"   Track Data: {json.dumps(track, indent=2)}")
                
                try:
                    artist = track.get('artist', '')
                    name = track.get('name', '')
                    
                    if not artist or not name:
                        print(f"SKIPPING: Missing required data")
                        print(f"Artist: '{artist}' | Name: '{name}'")
                        enriched_tracks.append(track)
                        failed_enrichments += 1
                        continue
                    
                    print(f"Track: '{name}' by '{artist}'")
                    
                    print(f"Fetching tags...")
                    tags = self._get_track_tags_verbose(artist, name)
                    print(f"Tags result: {tags}")

                    print(f"Fetching similar tracks...")
                    similar = self._get_similar_tracks_verbose(artist, name)
                    print(f"Similar tracks result: {len(similar)} tracks found")
                    
                    enriched_track = track.copy()
                    enriched_track['lastfm_tags'] = tags
                    enriched_track['similar_tracks'] = similar
                    enriched_track['enriched'] = True
                    enriched_track['enrichment_timestamp'] = time.time()
                    
                    enriched_tracks.append(enriched_track)
                    successful_enrichments += 1
                    
                    print(f"Successfully enriched track {i+1}")
                    
                    if i < len(tracks[:10]) - 1: 
                        print(f"Rate limiting: sleeping 200ms...")
                        time.sleep(0.2)
                    
                except Exception as e:
                    print(f"ERROR enriching track {i+1}: {e}")
                    print(f"Exception type: {type(e).__name__}")
                    enriched_tracks.append(track)
                    failed_enrichments += 1
                    continue
            
            print(f"\n{'='*60}")
            print(f"ENRICHMENT SUMMARY:")
            print(f"Successful: {successful_enrichments}")
            print(f"Failed: {failed_enrichments}")
            print(f"Total processed: {len(enriched_tracks)}")
            print(f"{'='*60}")
            
            result = {
                'enriched_tracks': enriched_tracks,
                'total_enriched': len(enriched_tracks),
                'successful_enrichments': successful_enrichments,
                'failed_enrichments': failed_enrichments,
                'lastfm_used': True,
                'processing_time': time.time()
            }
            
            print(f"Returning result with {len(enriched_tracks)} tracks")
            return json.dumps(result)
            
        except Exception as e:
            print(f"CRITICAL ERROR in Last.fm enrichment: {e}")
            print(f"Exception type: {type(e).__name__}")
            import traceback
            print(f"Full traceback:\n{traceback.format_exc()}")
            return json.dumps({
                'error': str(e),
                'enriched_tracks': [],
                'lastfm_used': False
            })
    
    def _get_track_tags_verbose(self, artist: str, track: str) -> List[str]:
        """Get semantic tags from Last.fm with verbose logging"""
        print(f"API Call: Getting tags for '{track}' by '{artist}'")
        
        params = {
            'method': 'track.gettoptags',
            'artist': artist,
            'track': track,
            'api_key': self.api_key,
            'format': 'json'
        }
        
        print(f"Request params: {params}")
        print(f"Request URL: {self.base_url}")
        
        try:
            print(f"Making HTTP request...")
            response = requests.get(self.base_url, params=params, timeout=10)
            print(f"Response status: {response.status_code}")
            print(f"Response size: {len(response.content)} bytes")
            
            if response.status_code != 200:
                print(f"HTTP Error: Status {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                print(f"Response content: {response.text[:200]}...")
                return []
            
            print(f" HTTP request successful")
            data = response.json()
            print(f"Parsed JSON response")
            print(f"Response keys: {list(data.keys())}")
            

            if 'toptags' in data and 'tag' in data['toptags']:
                tags_data = data['toptags']['tag']
                print(f"Found 'toptags.tag' in response")
                print(f"Tags data type: {type(tags_data)}")
                
                if isinstance(tags_data, list):
                    print(f"Processing {len(tags_data)} tags from list")
                    tags = [tag['name'] for tag in tags_data[:8] if 'name' in tag]
                    print(f"Extracted {len(tags)} valid tags: {tags}")
                    return tags
                elif isinstance(tags_data, dict) and 'name' in tags_data:
                    print(f"Processing single tag from dict")
                    tag_name = tags_data['name']
                    print(f"Extracted single tag: {tag_name}")
                    return [tag_name]
                else:
                    print(f"Unexpected tags data format: {tags_data}")
            else:
                print(f"No 'toptags.tag' found in response")
                print(f"Full response: {json.dumps(data, indent=2)}")
            
            if 'error' in data:
                print(f"Last.fm API error: {data.get('message', 'Unknown error')}")
                print(f" Error code: {data.get('error', 'No code')}")
            
        except requests.exceptions.Timeout:
            print(f"Request timed out after 10 seconds")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON decode failed: {e}")
            print(f"Response content: {response.text[:200]}...")
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
        
        print(f"Returning empty tags list")
        return []
    
    def _get_similar_tracks_verbose(self, artist: str, track: str) -> List[Dict]:
        """Get similar tracks from Last.fm with verbose logging"""
        print(f"API Call: Getting similar tracks for '{track}' by '{artist}'")
        
        params = {
            'method': 'track.getsimilar',
            'artist': artist,
            'track': track,
            'api_key': self.api_key,
            'format': 'json',
            'limit': 5
        }
        
        print(f" Request params: {params}")
        
        try:
            print(f"Making HTTP request...")
            response = requests.get(self.base_url, params=params, timeout=10)
            print(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"HTTP Error: Status {response.status_code}")
                return []
            
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            
            if 'similartracks' in data and 'track' in data['similartracks']:
                similar_data = data['similartracks']['track']
                print(f"Similar tracks data type: {type(similar_data)}")
                
                if isinstance(similar_data, list):
                    print(f"Processing {len(similar_data)} similar tracks")
                    tracks = []
                    for track_item in similar_data:
                        if 'name' in track_item and 'artist' in track_item:
                            track_info = {
                                'name': track_item['name'],
                                'artist': track_item['artist']['name'] if isinstance(track_item['artist'], dict) else str(track_item['artist']),
                                'match': float(track_item.get('match', 0)),
                                'url': track_item.get('url', '')
                            }
                            tracks.append(track_info)
                            print(f"{track_info['name']} by {track_info['artist']} (match: {track_info['match']})")
                    print(f"Extracted {len(tracks)} valid similar tracks")
                    return tracks
                elif isinstance(similar_data, dict) and 'name' in similar_data:
                    print(f"      📊 Processing single similar track")
                    track_info = {
                        'name': similar_data['name'],
                        'artist': similar_data['artist']['name'] if isinstance(similar_data['artist'], dict) else str(similar_data['artist']),
                        'match': float(similar_data.get('match', 0)),
                        'url': similar_data.get('url', '')
                    }
                    print(f"Extracted similar track: {track_info}")
                    return [track_info]
                else:
                    print(f"Unexpected similar tracks format: {similar_data}")
            else:
                print(f"No 'similartracks.track' found in response")
                print(f"Full response: {json.dumps(data, indent=2)}")
            
        except Exception as e:
            print(f" Error getting similar tracks: {e}")
            print(f"Traceback: {traceback.format_exc()}")
        
        print(f"Returning empty similar tracks list")
        return []
    
    async def _arun(
        self, 
        track_data: str, 
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, track_data, run_manager)

# def test_verbose_lastfm():
#     print(f"🚀 STARTING VERBOSE LAST.FM TEST")
#     print(f"{'='*80}")
    
#     # Simple test data
#     test_tracks = [
#         {
#             'id': 'test1',
#             'name': 'Bohemian Rhapsody',
#             'artist': 'Queen',
#             'album': 'A Night at the Opera'
#         }
#     ]
    
#     try:
#         api_key = os.getenv('LASTFM_API_KEY')
#         print(f"🔑 Environment API key: {'Found' if api_key else 'Not found'}")
#         tool = VerboseLastFmEnrichmentTool(api_key=api_key)
#         print(f"\RUNNING ENRICHMENT TEST")
#         test_input = json.dumps(test_tracks)
#         result = tool.invoke(test_input)
#         print(f"\n{'='*80}")
#         print(f"📤 FINAL RESULT:")
#         print(f"{'='*80}")
#         try:
#             data = json.loads(result)
#             print(json.dumps(data, indent=2))
#         except:
#             print(f"Raw result: {result}")
#     except Exception as e:
#         print(f"TEST FAILED: {e}")
#         import traceback
#         print(f"Full traceback:\n{traceback.format_exc()}")

# if __name__ == "__main__":
#     test_verbose_lastfm()