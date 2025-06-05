from typing import Optional
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import asyncio
from dotenv import load_dotenv
from configs.configurations import config

load_dotenv()


class IntelligentRankingTool(BaseTool):
    name: str = "intelligent_ranking"
    description: str = "Uses LLM to intelligently rank and filter tracks based on context"
    
    def _run(
        self, 
        ranking_input: str, 
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:    
        try:
            data = json.loads(ranking_input)
            tracks = data['tracks']
            context = data['context']
            mood = data['mood']
            
            llm = config.llm
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a world-class music curator with deep understanding of human psychology, musical aesthetics, and cultural context.
                    Your task is to rank tracks based on sophisticated musical and psychological criteria."""),
                                    ("human", """
                    User Context:
                    Mood Analysis: {mood_analysis}
                    Musical Context: {musical_context}

                    Candidate Tracks:
                    {tracks_summary}

                    Rank these tracks (by index) considering:
                    1. Emotional resonance with the user's psychological state
                    2. Musical sophistication and aesthetic fit
                    3. Context appropriateness (activity, time, social setting)
                    4. Balance between comfort and discovery
                    5. Sonic characteristics matching the mood
                    6. Cultural and stylistic coherence

                    Return a JSON object with:
                    {{
                        "ranked_indices": [list of track indices in order of recommendation quality],
                        "reasoning": "explanation of ranking methodology",
                        "top_pick_explanation": "why the top choice is perfect for this context"
                    }}
                """)
            ])
            
            tracks_summary = []
            for i, track in enumerate(tracks[:15]): 
                estimated_features = track.get('estimated_features', {})
                summary = {
                    'index': i,
                    'name': track['name'],
                    'artist': track['artist'],
                    'source': track.get('source', 'unknown'),
                    'popularity': track.get('popularity', 0),
                    'genre': track.get('genre', 'unknown'),
                    'audio_features': {
                        'energy': estimated_features.get('energy', 0.5),
                        'valence': estimated_features.get('valence', 0.5),
                        'danceability': estimated_features.get('danceability', 0.5),
                        'acousticness': estimated_features.get('acousticness', 0.3),
                        'tempo': estimated_features.get('tempo', 120)
                    },
                    'tags': track.get('lastfm_tags', [])[:5],
                    'has_preview': bool(track.get('preview_url')),
                    'relevance_score': track.get('relevance_score', 0)
                }
                tracks_summary.append(summary)
            
            chain = prompt | llm | StrOutputParser()
            
            result = chain.invoke({
                'mood_analysis': json.dumps(mood, indent=2),
                'musical_context': json.dumps(context, indent=2),
                'tracks_summary': json.dumps(tracks_summary, indent=2)
            })
            
            try:
                ranking_result = json.loads(result)
                ranked_indices = ranking_result.get('ranked_indices', list(range(len(tracks))))
                ranked_tracks = []
                
                for idx in ranked_indices:
                    if idx < len(tracks):
                        track = tracks[idx].copy()
                        track['ranking_score'] = len(ranked_indices) - ranked_indices.index(idx)
                        ranked_tracks.append(track)
                
                return json.dumps({
                    'ranked_tracks': ranked_tracks,
                    'reasoning': ranking_result.get('reasoning', ''),
                    'top_pick_explanation': ranking_result.get('top_pick_explanation', ''),
                    'ranking_method': 'llm_intelligent'
                })
                
            except json.JSONDecodeError:
                scored_tracks = []
                for track in tracks:
                    score = track.get('relevance_score', 0)
                    score += track.get('popularity', 0) / 10
                    if track.get('preview_url'):
                        score += 5
                    track['ranking_score'] = score
                    scored_tracks.append(track)
                
                scored_tracks.sort(key=lambda x: x.get('ranking_score', 0), reverse=True)
                return json.dumps({
                    'ranked_tracks': scored_tracks,
                    'reasoning': 'Used fallback ranking based on popularity and availability',
                    'top_pick_explanation': 'Selected based on overall relevance and data quality',
                    'ranking_method': 'fallback_scoring'
                })
            
        except Exception as e:
            print(f"Ranking error: {e}")
            return json.dumps({
                'error': str(e),
                'ranked_tracks': data.get('tracks', []),
                'ranking_method': 'error_fallback'
            })
    
    async def _arun(
        self, 
        ranking_input: str, 
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, ranking_input, run_manager)

