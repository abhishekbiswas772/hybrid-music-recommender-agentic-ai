from tools.music_tool_merger import ModernMusicRecommender
from datetime import datetime
from typing import Dict


class ModernMusicBotInterface:
    def __init__(self):
        self.recommender = ModernMusicRecommender()
        self.active_sessions = {}
    
    async def chat(self, user_id: str, message: str) -> Dict:
        
        try:
            response = await self.recommender.get_recommendations(user_id, message)
            return {
                'response': response.get('message', 'Here are some recommendations for you!'),
                'recommendations': response.get('recommendations', []),
                'context': {
                    'mood_analysis': response.get('mood_analysis', {}),
                    'musical_context': response.get('musical_context', {}),
                    'total_candidates': response.get('total_candidates', 0)
                },
                'reasoning': response.get('reasoning', ''),
                'session_id': f"{user_id}_{datetime.now().strftime('%Y%m%d%H')}",
                'type': response.get('type', 'chat_response')
            }
            
        except Exception as e:
            return {
                'response': f"I'm having trouble processing that request. Could you try again?",
                'error': str(e),
                'recommendations': [],
                'type': 'error_response'
            }
    
    async def provide_feedback(self, user_id: str, track_id: str, rating: float, feedback: str = ""):
        try:
            await self.recommender.record_feedback(user_id, track_id, rating, feedback)
            
            return {
                'message': 'Thanks for the feedback! I\'ll use this to improve future recommendations.',
                'status': 'success'
            }
        except Exception as e:
            return {
                'message': 'Sorry, I couldn\'t record your feedback right now.',
                'status': 'error',
                'error': str(e)
            }



