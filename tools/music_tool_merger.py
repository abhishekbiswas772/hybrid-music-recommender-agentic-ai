from configs.configurations import config
from typing import Dict
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from tools.musical_context_tool import MusicalContextTool
from tools.mood_analysis_tool import MoodAnalysisTool
from tools.music_search_tool import FreeMusicSearchTool
from tools.lastfm_tool import LastFmEnrichmentTool
from tools.intelligent_ranking_tool import IntelligentRankingTool

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from datetime import datetime
import json

class ModernMusicRecommender:
    """Modern LangChain music recommender using new patterns"""
    
    def __init__(self):
        self.llm = config.llm
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = Chroma(
            collection_name="music_preferences",
            embedding_function=self.embeddings,
            persist_directory="./chroma_db"
        )
        
        # ✅ NEW: Initialize tools
        self.tools = {
            "mood_analyzer": MoodAnalysisTool(),
            "musical_context_extractor": MusicalContextTool(),
            "free_music_search": FreeMusicSearchTool(),  # ✅ FIXED: Updated from spotify_search
            "lastfm_enrichment": LastFmEnrichmentTool(),
            "intelligent_ranking": IntelligentRankingTool()
        }
        
        # ✅ NEW: Modern chat history management
        self.store = {}  # Session store
        
        # Create the modern recommendation chain
        self._create_recommendation_chain()
    
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Get or create chat history for session"""
        if session_id not in self.store:
            self.store[session_id] = InMemoryChatMessageHistory()
        return self.store[session_id]
    
    def _create_recommendation_chain(self):
        """Create modern LangChain recommendation chain"""
        
        # ✅ NEW: Updated prompt to reference correct tools
        system_prompt = """You are an intelligent music curator and recommender. You have access to several specialized tools for music analysis and recommendation.
        Your goal is to understand the user's musical needs deeply and provide personalized, contextually appropriate music recommendations.

        Available Tools:
        - mood_analyzer: Analyzes user's emotional state from text
        - musical_context_extractor: Extracts musical context and preferences
        - free_music_search: Searches multiple free APIs for music (Deezer, iTunes, Last.fm, etc.)
        - lastfm_enrichment: Adds semantic tags and similar track data
        - intelligent_ranking: Ranks tracks using AI-based criteria

        Process:
        1. Analyze the user's mood and emotional state
        2. Extract musical context and activity preferences  
        3. Search for candidate tracks using free music APIs
        4. Enrich tracks with semantic data from Last.fm
        5. Rank tracks intelligently based on context
        6. Provide natural, conversational recommendations

        Always explain your reasoning and show understanding of the user's needs.
        """

        # ✅ NEW: Modern prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # ✅ NEW: Create recommendation workflow
        self.recommendation_chain = (
            RunnablePassthrough.assign(
                # Get user preferences from vector store
                user_context=RunnableLambda(self._get_user_context),
                # Analyze mood
                mood_analysis=RunnableLambda(self._analyze_mood),
                # Extract musical context
                musical_context=RunnableLambda(self._extract_context),
            )
            | RunnablePassthrough.assign(
                # Search for music
                search_results=RunnableLambda(self._search_music),
            )
            | RunnablePassthrough.assign(
                # Enrich with Last.fm
                enriched_tracks=RunnableLambda(self._enrich_tracks),
            )
            | RunnablePassthrough.assign(
                # Rank intelligently
                ranked_recommendations=RunnableLambda(self._rank_tracks),
            )
            | RunnableLambda(self._format_response)
        )
        
        # ✅ NEW: Add chat history support
        self.chain_with_history = RunnableWithMessageHistory(
            self.recommendation_chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="history"
        )
    
    async def _get_user_context(self, inputs: Dict) -> Dict:
        """Retrieve user context from vector store"""
        try:
            user_id = inputs.get('user_id', 'default')
            query = inputs.get('input', '')
            
            # Search for relevant user preferences
            docs = self.vectorstore.similarity_search(
                query, 
                k=5,
                filter={"user_id": user_id}
            )
            
            preferences = []
            for doc in docs:
                preferences.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata
                })
            
            return {
                'user_preferences': preferences,
                'preference_count': len(preferences)
            }
        except Exception as e:
            print(f"Error getting user context: {e}")
            return {'user_preferences': [], 'preference_count': 0}
    
    async def _analyze_mood(self, inputs: Dict) -> Dict:
        """Analyze user's mood"""
        try:
            query = inputs.get('input', '')
            mood_tool = self.tools["mood_analyzer"]
            
            result = mood_tool.invoke(query)
            mood_data = json.loads(result) if isinstance(result, str) else result
            
            return mood_data
        except Exception as e:
            print(f"Error analyzing mood: {e}")
            return {
                'primary_emotion': 'neutral',
                'intensity': 0.5,
                'mood_descriptors': ['neutral']
            }
    
    async def _extract_context(self, inputs: Dict) -> Dict:
        """Extract musical context"""
        try:
            query = inputs.get('input', '')
            context_tool = self.tools["musical_context_extractor"]
            
            result = context_tool.invoke(query)
            context_data = json.loads(result) if isinstance(result, str) else result
            
            return context_data
        except Exception as e:
            print(f"Error extracting context: {e}")
            return {
                'activity_type': 'general',
                'energy_preference': 0.5,
                'genre_hints': []
            }
    
    async def _search_music(self, inputs: Dict) -> Dict:
        """Search for music using free APIs"""
        try:
            # Combine mood and context for search
            mood_data = inputs.get('mood_analysis', {})
            context_data = inputs.get('musical_context', {})
            
            search_params = {
                'mood_descriptors': mood_data.get('mood_descriptors', []),
                'genre_hints': context_data.get('genre_hints', []),
                'activity_type': context_data.get('activity_type', ''),
                'energy_preference': context_data.get('energy_preference', 0.5)
            }
            
            search_tool = self.tools["free_music_search"]
            result = search_tool.invoke(json.dumps(search_params))
            search_data = json.loads(result) if isinstance(result, str) else result
            
            return search_data
        except Exception as e:
            print(f"Error searching music: {e}")
            return {'tracks': [], 'total_found': 0}
    
    async def _enrich_tracks(self, inputs: Dict) -> Dict:
        """Enrich tracks with Last.fm data"""
        try:
            search_results = inputs.get('search_results', {})
            tracks = search_results.get('tracks', [])
            
            if not tracks:
                return {'enriched_tracks': [], 'total_enriched': 0}
            
            # Take top tracks for enrichment
            enrichment_tool = self.tools["lastfm_enrichment"]
            result = enrichment_tool.invoke(json.dumps(tracks[:10]))
            enrichment_data = json.loads(result) if isinstance(result, str) else result
            
            return enrichment_data
        except Exception as e:
            print(f"Error enriching tracks: {e}")
            return {'enriched_tracks': [], 'total_enriched': 0}
    
    async def _rank_tracks(self, inputs: Dict) -> Dict:
        """Rank tracks intelligently"""
        try:
            enriched_data = inputs.get('enriched_tracks', {})
            tracks = enriched_data.get('enriched_tracks', [])
            
            if not tracks:
                return {'ranked_tracks': [], 'reasoning': 'No tracks to rank'}
            
            mood_data = inputs.get('mood_analysis', {})
            context_data = inputs.get('musical_context', {})
            
            ranking_input = {
                'tracks': tracks,
                'mood': mood_data,
                'context': context_data
            }
            
            ranking_tool = self.tools["intelligent_ranking"]
            result = ranking_tool.invoke(json.dumps(ranking_input))
            ranking_data = json.loads(result) if isinstance(result, str) else result
            
            return ranking_data
        except Exception as e:
            print(f"Error ranking tracks: {e}")
            return {'ranked_tracks': tracks if 'enriched_tracks' in inputs else [], 'reasoning': 'Ranking failed, using original order'}
    
    async def _format_response(self, inputs: Dict) -> Dict:
        """Format final response"""
        try:
            ranked_data = inputs.get('ranked_recommendations', {})
            tracks = ranked_data.get('ranked_tracks', [])
            reasoning = ranked_data.get('reasoning', '')
            
            mood_data = inputs.get('mood_analysis', {})
            context_data = inputs.get('musical_context', {})
            user_context = inputs.get('user_context', {})
            
            # ✅ NEW: Use LLM to generate natural response
            response_prompt = ChatPromptTemplate.from_template("""
Based on the user's request and the music analysis, provide a natural, conversational response with recommendations.

User Request: {user_input}
Mood Analysis: {mood_summary}
Musical Context: {context_summary}
User History: {user_history}

Top Recommendations:
{tracks_summary}

AI Reasoning: {ai_reasoning}

Generate a warm, personalized response that:
1. Shows understanding of the user's needs
2. Explains why these songs were chosen
3. Highlights interesting connections
4. Feels conversational and insightful

Keep it concise but meaningful (2-3 sentences).
""")
            
            # Prepare summaries
            tracks_summary = []
            for i, track in enumerate(tracks[:5], 1):
                summary = f"{i}. {track['name']} by {track['artist']}"
                if track.get('lastfm_tags'):
                    summary += f" (Tags: {', '.join(track['lastfm_tags'][:3])})"
                tracks_summary.append(summary)
            
            response_chain = response_prompt | self.llm | StrOutputParser()
            
            natural_response = response_chain.invoke({
                'user_input': inputs.get('input', ''),
                'mood_summary': f"Mood: {mood_data.get('primary_emotion', 'neutral')} (intensity: {mood_data.get('intensity', 0.5)})",
                'context_summary': f"Activity: {context_data.get('activity_type', 'general')}, Energy: {context_data.get('energy_preference', 0.5)}",
                'user_history': f"Found {user_context.get('preference_count', 0)} previous interactions",
                'tracks_summary': '\n'.join(tracks_summary),
                'ai_reasoning': reasoning
            })
            
            return {
                'message': natural_response,
                'recommendations': tracks[:5],
                'mood_analysis': mood_data,
                'musical_context': context_data,
                'total_candidates': len(tracks),
                'reasoning': reasoning,
                'type': 'music_recommendations'
            }
            
        except Exception as e:
            print(f"Error formatting response: {e}")
            return {
                'message': "I found some music for you! Here are my recommendations.",
                'recommendations': inputs.get('ranked_recommendations', {}).get('ranked_tracks', [])[:5],
                'type': 'fallback_response'
            }
    
    async def get_recommendations(self, user_id: str, user_input: str) -> Dict:
        """Main recommendation method"""
        try:
            # Update user context in vector store
            await self._update_user_context(user_id, user_input)
            
            # ✅ NEW: Use modern chain with history
            session_id = f"{user_id}_music"
            
            result = await self.chain_with_history.ainvoke(
                {
                    "input": user_input,
                    "user_id": user_id
                },
                config={"configurable": {"session_id": session_id}}
            )
            
            return result
            
        except Exception as e:
            print(f"Error in get_recommendations: {e}")
            return {
                'error': str(e),
                'message': "I encountered an issue processing your request. Could you try rephrasing?",
                'recommendations': [],
                'type': 'error_response'
            }
    
    async def _update_user_context(self, user_id: str, user_input: str):
        """Update user context in vector store"""
        try:
            doc = Document(
                page_content=f"User query: {user_input}",
                metadata={
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'user_query'
                }
            )
            
            self.vectorstore.add_documents([doc])
            
        except Exception as e:
            print(f"Error updating user context: {e}")
    
    async def record_feedback(self, user_id: str, track_id: str, rating: float, feedback: str = ""):
        """Record user feedback for learning"""
        try:
            feedback_doc = Document(
                page_content=f"Track feedback: {track_id} rated {rating}/5. {feedback}",
                metadata={
                    'user_id': user_id,
                    'track_id': track_id,
                    'rating': rating,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'feedback'
                }
            )
            
            self.vectorstore.add_documents([feedback_doc])
            
        except Exception as e:
            print(f"Error recording feedback: {e}")

