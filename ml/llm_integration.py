from datetime import datetime
import numpy as np
import pandas as pd
import json

class LLMRLIntegrator:
    """Integrates LLM reasoning with RL personalization"""
    
    def __init__(self, config):
        self.config = config
    
    def enhance_llm_prompt_with_rl_insights(self, base_prompt: str, user_id: int, rl_insights) -> str:
        """Enhance LLM prompt with RL-learned user preferences"""
        
        if not rl_insights.get('model_exists', False):
            return base_prompt
        
        # Extract key preferences from RL insights
        preferences = rl_insights.get('preference_patterns', {})
        
        enhancement_parts = []
        
        # Add genre preferences
        if 'preferred_genres' in preferences:
            top_genres = preferences['preferred_genres'][:3]
            enhancement_parts.append(f"User typically enjoys: {', '.join(top_genres)}")
        
        # Add artist preferences
        if 'preferred_artists' in preferences:
            top_artists = preferences['preferred_artists'][:2]
            enhancement_parts.append(f"Often likes music by: {', '.join(top_artists)}")
        
        # Add energy level preferences
        if 'average_energy' in preferences:
            energy = preferences['average_energy']
            energy_desc = "high-energy" if energy > 0.7 else "moderate-energy" if energy > 0.4 else "low-energy"
            enhancement_parts.append(f"Prefers {energy_desc} music")
        
        # Add temporal patterns
        if 'temporal_preferences' in preferences:
            current_hour = datetime.now().hour
            if str(current_hour) in preferences['temporal_preferences']:
                time_pref = preferences['temporal_preferences'][str(current_hour)]
                enhancement_parts.append(f"At this time usually prefers {time_pref}")
        
        # Add mood patterns
        if 'mood_patterns' in preferences:
            common_moods = preferences['mood_patterns'][:2]
            enhancement_parts.append(f"Often seeks {' and '.join(common_moods)} vibes")
        
        # Build enhanced prompt
        if enhancement_parts:
            enhancement = f"\n\nPersonalization Context (learned from user behavior): {'; '.join(enhancement_parts)}"
            enhanced_prompt = base_prompt + enhancement
        else:
            enhanced_prompt = base_prompt
        
        return enhanced_prompt
    
    def combine_llm_rl_scores(self, llm_score: float, rl_score: float, rl_confidence: float) -> float:
        """Combine LLM and RL scores into final recommendation score"""
        
        # Weight based on RL confidence
        if rl_confidence > 0.8:
            # High confidence: favor RL heavily
            combined_score = (llm_score * 0.3) + (rl_score * 0.7)
        elif rl_confidence > 0.5:
            # Medium confidence: balanced approach
            combined_score = (llm_score * 0.5) + (rl_score * 0.5)
        else:
            # Low confidence: favor LLM
            combined_score = (llm_score * 0.7) + (rl_score * 0.3)
        
        return combined_score
    
    def generate_hybrid_explanation(self, llm_reasoning: str, rl_insights, confidence: float) -> str:
        """Generate explanation that combines LLM reasoning with RL insights"""
        
        explanation_parts = [llm_reasoning]
        
        if confidence > 0.5:
            if rl_insights.get('model_exists'):
                explanation_parts.append(
                    "I've also personalized these recommendations based on your listening history and preferences."
                )
                
                if confidence > 0.8:
                    explanation_parts.append(
                        "I'm very confident these match your taste based on your past ratings."
                    )
                elif confidence > 0.6:
                    explanation_parts.append(
                        "These recommendations are tailored to your preferences with good confidence."
                    )
            else:
                explanation_parts.append(
                    "Rate more tracks to help me learn your preferences and provide better personalization!"
                )
        
        return " ".join(explanation_parts)

