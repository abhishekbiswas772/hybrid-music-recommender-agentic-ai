from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class MoodAnalysis(BaseModel):
    """Structured mood analysis output"""
    primary_emotion : str = Field(description="Primary emotion state")
    intensity : float = Field(description="Emotional intensity from 0 - 1") 
    valence : float = Field(description="Emotional valence from -1 to 1")
    arousal : float = Field(description="Emotional arousal from 0 to 1")
    dominance : float = Field(description="Sense of control from 0 to 1")
    mood_descriptors : List[str] = Field(description="Specific mood words")
    context_factor : List[str] = Field(description="Contextual influences")


class MusicalContext(BaseModel):
    """Structured musical context output"""
    activity_type: str = Field(description="Type of activity or situation")
    energy_preference: float = Field(description="Preferred energy level 0-1")
    familiarity_preference: float = Field(description="Want familiar vs new music 0-1")
    social_context: str = Field(description="Social setting")  
    temporal_context: str = Field(description="Time-related context")  
    genre_hints: List[str] = Field(description="Suggested genres")
    sonic_descriptors: List[str] = Field(description="Sound characteristics")
    instrumental_preferences: List[str] = Field(description="Preferred instruments")

class TrackRecommendation(BaseModel):
    """Structured track recommendation"""
    track_id : str
    name : str
    artist : str
    album : str
    confidence_score : float = Field(description="Recommendation confidence 0 - 1")
    reasoning : str = Field(description="why this truck was recommended") 
    spotify_features : Dict
    tags : List[str]
    preview_url : Optional[str] = None



class RecommendationResponse(BaseModel):
    """Complete recommendation response"""
    recommendations : List[TrackRecommendation]
    explanation : str = Field(description="Natural language explanation")
    mood_analysis : MoodAnalysis
    musical_context : MusicalContext
    total_candidates : int