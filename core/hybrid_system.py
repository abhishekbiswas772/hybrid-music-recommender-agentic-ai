import json
from typing import Dict, List
from datetime import datetime
from dataclasses import dataclass

from main import ModernMusicRecommender
from ml.reinforcement_learning import ReinforcementLearningEngine
from ml.llm_integration import LLMRLIntegrator
from services.analytics_service import AnalyticsService

@dataclass
class RecommendationRequest:
    user_id: int
    query: str
    context: Dict
    max_results: int = 5
    use_rl_enhancement: bool = True

@dataclass
class RecommendationResponse:
    tracks: List[Dict]
    reasoning: str
    llm_insights: Dict
    rl_insights: Dict
    hybrid_score: float
    processing_time_ms: int

class HybridMusicSystem:
    def __init__(self, config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.llm_recommender = ModernMusicRecommender()
        self.rl_engine = ReinforcementLearningEngine(config.rl, db_manager)
        self.llm_rl_integrator = LLMRLIntegrator(config)
        self.analytics_service = AnalyticsService(db_manager)
        self.user_models = {}
        self.user_contexts = {}
    
    async def get_recommendations(self, request: RecommendationRequest) -> RecommendationResponse:
        start_time = datetime.now()
        try:
            user_context = await self._get_enhanced_user_context(request.user_id)
            enhanced_query = await self._enhance_query_with_patterns(
                request.query, request.user_id, user_context
            )
            llm_response = await self.llm_recommender.get_recommendations(
                str(request.user_id), enhanced_query
            )
            if request.use_rl_enhancement and self._has_sufficient_training_data(request.user_id):
                rl_enhanced_tracks = await self._apply_rl_enhancement(
                    llm_response['recommendations'], request.user_id, user_context
                )
            else:
                rl_enhanced_tracks = llm_response['recommendations']
            hybrid_reasoning = await self._generate_hybrid_reasoning(
                llm_response, rl_enhanced_tracks, user_context
            )
            hybrid_score = self._calculate_hybrid_confidence(
                llm_response, rl_enhanced_tracks, user_context
            )
            await self._log_interaction(request, rl_enhanced_tracks, user_context)
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return RecommendationResponse(
                tracks=rl_enhanced_tracks[:request.max_results],
                reasoning=hybrid_reasoning,
                llm_insights=self._extract_llm_insights(llm_response),
                rl_insights=self._extract_rl_insights(request.user_id),
                hybrid_score=hybrid_score,
                processing_time_ms=int(processing_time)
            )
            
        except Exception as e:
            return await self._fallback_recommendations(request, str(e))
    
    async def _get_enhanced_user_context(self, user_id: int) -> Dict:
        if user_id in self.user_contexts:
            cache_time = self.user_contexts[user_id]['timestamp']
            if (datetime.now() - cache_time).seconds < 300: 
                return self.user_contexts[user_id]['context']
        
        user_data = self.db_manager.get_user_data(user_id)
        recent_interactions = self.db_manager.get_recent_interactions(user_id, limit=20)
        feedback_patterns = self.db_manager.get_feedback_patterns(user_id)
        rl_insights = self.rl_engine.get_user_insights(user_id)
        temporal_patterns = self.analytics_service.get_temporal_patterns(user_id)
        context = {
            'user_data': user_data,
            'recent_interactions': recent_interactions,
            'feedback_patterns': feedback_patterns,
            'rl_insights': rl_insights,
            'temporal_patterns': temporal_patterns,
            'timestamp': datetime.now()
        }
        
        self.user_contexts[user_id] = {'context': context, 'timestamp': datetime.now()}
        return context
    
    async def _enhance_query_with_patterns(self, query: str, user_id: int, context: Dict) -> str:
        rl_insights = context.get('rl_insights', {})
        feedback_patterns = context.get('feedback_patterns', {})
        enhancements = []
        if rl_insights.get('top_genres'):
            top_genres = rl_insights['top_genres'][:3]
            enhancements.append(f"User typically enjoys: {', '.join(top_genres)}")

        if feedback_patterns.get('preferred_moods'):
            moods = feedback_patterns['preferred_moods'][:2]
            enhancements.append(f"Often seeks {' and '.join(moods)} music")

        current_hour = datetime.now().hour
        temporal_patterns = context.get('temporal_patterns', {})
        if str(current_hour) in temporal_patterns.get('hourly_preferences', {}):
            hour_pref = temporal_patterns['hourly_preferences'][str(current_hour)]
            enhancements.append(f"At this time usually prefers {hour_pref}")
        
        if rl_insights.get('average_energy_preference'):
            energy = rl_insights['average_energy_preference']
            energy_desc = "high" if energy > 0.7 else "moderate" if energy > 0.4 else "low"
            enhancements.append(f"Typically prefers {energy_desc} energy music")
        
        if enhancements:
            enhanced_query = f"{query}\n\nUser Pattern Context: {'; '.join(enhancements)}"
        else:
            enhanced_query = query
        
        return enhanced_query
    
    async def _apply_rl_enhancement(self, tracks: List[Dict], user_id: int, context: Dict) -> List[Dict]:
        enhanced_tracks = []
        
        for track in tracks:
            rl_prediction = self.rl_engine.predict_user_rating(
                user_id, track, context
            )
            base_score = track.get('ranking_score', 0)
            rl_bonus = (rl_prediction - 3.0) * 5 
            diversity_penalty = self._calculate_diversity_penalty(track, context['recent_interactions'])
            enhanced_score = base_score + rl_bonus - diversity_penalty
            enhanced_track = track.copy()
            enhanced_track.update({
                'rl_predicted_rating': rl_prediction,
                'rl_bonus': rl_bonus,
                'diversity_penalty': diversity_penalty,
                'enhanced_score': enhanced_score,
                'rl_confidence': self.rl_engine.get_prediction_confidence(user_id, track)
            })
            
            enhanced_tracks.append(enhanced_track)
        enhanced_tracks.sort(key=lambda x: x.get('enhanced_score', 0), reverse=True)

        return enhanced_tracks
    
    def _calculate_diversity_penalty(self, track: Dict, recent_interactions: List[Dict]) -> float:
        
        penalty = 0.0
        track_artist = track.get('artist', '').lower()
        recent_artists = [
            r.get('artist', '').lower() 
            for interaction in recent_interactions 
            for r in json.loads(interaction.get('recommendations', '[]'))
        ]
        
        artist_count = recent_artists.count(track_artist)
        if artist_count > 0:
            penalty += artist_count * 2.0  
        
        track_genres = [tag.lower() for tag in track.get('lastfm_tags', [])]
        recent_genres = []
        for interaction in recent_interactions:
            for r in json.loads(interaction.get('recommendations', '[]')):
                recent_genres.extend([tag.lower() for tag in r.get('lastfm_tags', [])])
        
        genre_overlap = len(set(track_genres) & set(recent_genres[-10:]))  # Last 10 genres
        penalty += genre_overlap * 0.5
        
        return min(penalty, 10.0)  # Cap penalty
    
    async def _generate_hybrid_reasoning(self, llm_response: Dict, rl_tracks: List[Dict], context: Dict) -> str:
        llm_reasoning = llm_response.get('reasoning', '')
        rl_insights = []
        original_order = [t['name'] for t in llm_response.get('recommendations', [])]
        rl_order = [t['name'] for t in rl_tracks]
        
        if original_order != rl_order:
            rl_insights.append("I've personalized these recommendations based on your listening history")

        high_confidence_tracks = [t for t in rl_tracks if t.get('rl_confidence', 0) > 0.8]
        if high_confidence_tracks:
            rl_insights.append(f"I'm especially confident about {len(high_confidence_tracks)} of these recommendations")

        training_samples = context.get('rl_insights', {}).get('training_samples', 0)
        if training_samples > 20:
            rl_insights.append("My recommendations are well-tuned to your preferences")
        elif training_samples > 5:
            rl_insights.append("I'm still learning your preferences - rate more tracks for better recommendations")
        
        if rl_insights:
            combined_reasoning = f"{llm_reasoning}\n\nPersonalization Notes: {'. '.join(rl_insights)}."
        else:
            combined_reasoning = llm_reasoning
        
        return combined_reasoning
    
    def _calculate_hybrid_confidence(self, llm_response: Dict, rl_tracks: List[Dict], context: Dict) -> float:
        llm_confidence = 0.8 
        rl_insights = context.get('rl_insights', {})
        training_samples = rl_insights.get('training_samples', 0)
        model_accuracy = rl_insights.get('model_accuracy', 0.5)
        
        if training_samples >= 20:
            rl_confidence = model_accuracy
        elif training_samples >= 5:
            rl_confidence = model_accuracy * 0.7
        else:
            rl_confidence = 0.3  
        
        if training_samples >= 5:
            hybrid_confidence = (llm_confidence * 0.6) + (rl_confidence * 0.4)
        else:
            hybrid_confidence = llm_confidence * 0.9
        
        return min(max(hybrid_confidence, 0.0), 1.0)
    
    def _has_sufficient_training_data(self, user_id: int) -> bool:
        feedback_count = self.db_manager.get_user_feedback_count(user_id)
        return feedback_count >= self.config.rl.min_training_samples
    
    async def _log_interaction(self, request: RecommendationRequest, tracks: List[Dict], context: Dict):
        interaction_data = {
            'user_id': request.user_id,
            'query': request.query,
            'recommendations': tracks,
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'rl_enhanced': request.use_rl_enhancement and self._has_sufficient_training_data(request.user_id)
        }
        
        self.db_manager.log_interaction(interaction_data)
    
    def _extract_llm_insights(self, llm_response: Dict) -> Dict:
        return {
            'mood_analysis': llm_response.get('mood_analysis', {}),
            'musical_context': llm_response.get('musical_context', {}),
            'reasoning_quality': len(llm_response.get('reasoning', '')) > 50,
            'total_candidates': llm_response.get('total_candidates', 0)
        }
    
    def _extract_rl_insights(self, user_id: int) -> Dict:
        """Extract insights from RL system"""
        return self.rl_engine.get_user_insights(user_id)
    
    async def _fallback_recommendations(self, request: RecommendationRequest, error: str) -> RecommendationResponse:
        try:
            llm_response = await self.llm_recommender.get_recommendations(
                str(request.user_id), request.query
            )
            
            return RecommendationResponse(
                tracks=llm_response.get('recommendations', [])[:request.max_results],
                reasoning=f"Using LLM-only recommendations due to technical issue: {error}",
                llm_insights=self._extract_llm_insights(llm_response),
                rl_insights={},
                hybrid_score=0.5,
                processing_time_ms=0
            )
            
        except Exception as e:
            return RecommendationResponse(
                tracks=[],
                reasoning=f"Unable to generate recommendations: {e}",
                llm_insights={},
                rl_insights={},
                hybrid_score=0.0,
                processing_time_ms=0
            )
    
    async def process_feedback(self, user_id: int, track_id: str, rating: int, feedback_text: str) -> Dict:
        feedback_data = {
            'user_id': user_id,
            'track_id': track_id,
            'rating': rating,
            'feedback_text': feedback_text,
            'timestamp': datetime.now().isoformat()
        }
        
        self.db_manager.log_feedback(feedback_data)
        if self._has_sufficient_training_data(user_id):
            training_result = await self.rl_engine.update_user_model(user_id)
            if user_id in self.user_contexts:
                del self.user_contexts[user_id]
            
            return {
                'success': True,
                'model_updated': training_result.get('success', False),
                'new_accuracy': training_result.get('accuracy', 0),
                'message': 'Thank you! Your feedback helps improve recommendations.'
            }
        else:
            needed = self.config.rl.min_training_samples - self.db_manager.get_user_feedback_count(user_id)
            return {
                'success': True,
                'model_updated': False,
                'message': f'Thank you! Rate {needed} more tracks to unlock AI personalization.'
            }
    
    def get_ai_status(self, user_id: int) -> Dict:
        feedback_count = self.db_manager.get_user_feedback_count(user_id)
        rl_insights = self.rl_engine.get_user_insights(user_id)
        
        return {
            'llm_active': True,
            'rl_active': feedback_count >= self.config.rl.min_training_samples,
            'training_samples': feedback_count,
            'accuracy': rl_insights.get('model_accuracy', 0),
            'llm_creativity': 0.3,  
            'llm_context_length': 5,
            'rl_exploration': self.config.rl.exploration_rate,
            'rl_learning_rate': self.config.rl.learning_rate
        }
    
    def retrain_user_model(self, user_id: int) -> Dict:
        try:
            if not self._has_sufficient_training_data(user_id):
                return {
                    'success': False,
                    'message': f'Need at least {self.config.rl.min_training_samples} ratings to train model'
                }
            
            result = self.rl_engine.train_user_model(user_id)
            if user_id in self.user_contexts:
                del self.user_contexts[user_id]
            
            return {
                'success': result.get('success', False),
                'accuracy': result.get('accuracy', 0),
                'message': 'Model retrained successfully!' if result.get('success') else 'Training failed'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Training error: {str(e)}'
            }
    
    def get_learning_insights(self, user_id: int) -> Dict:
        return self.rl_engine.get_detailed_insights(user_id)
    
    def get_performance_metrics(self, user_id: int) -> Dict:
        return self.rl_engine.get_performance_history(user_id)
    
    def update_ai_config(self, user_id: int, config_updates: Dict):
        pass