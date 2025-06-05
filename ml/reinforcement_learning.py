
from datetime import datetime
from typing import Dict, List
import numpy as np
import pandas as pd
import json
import pickle
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging

logger = logging.getLogger(__name__)

class ReinforcementLearningEngine:
    """RL Engine that enhances LLM recommendations with personalized learning"""
    
    def __init__(self, config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.user_models = {}
        self.feature_scaler = StandardScaler()
        self.model_dir = "data/models"
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Load existing models
        self._load_models()
    
    def _load_models(self):
        """Load saved user models"""
        try:
            models_file = os.path.join(self.model_dir, "user_models.pkl")
            if os.path.exists(models_file):
                with open(models_file, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.user_models = saved_data.get('user_models', {})
                    self.feature_scaler = saved_data.get('feature_scaler', StandardScaler())
                logger.info(f"Loaded {len(self.user_models)} user models")
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            self.user_models = {}
    
    def _save_models(self):
        """Save user models to disk"""
        try:
            models_file = os.path.join(self.model_dir, "user_models.pkl")
            save_data = {
                'user_models': self.user_models,
                'feature_scaler': self.feature_scaler,
                'saved_at': datetime.now().isoformat()
            }
            with open(models_file, 'wb') as f:
                pickle.dump(save_data, f)
            logger.info("Models saved successfully")
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
    
    def extract_track_features(self, track: Dict, context: Dict = None) -> np.ndarray:
        """Extract features from track and context for RL model"""
        features = []
        
        # Track audio features
        estimated_features = track.get('estimated_features', {})
        features.extend([
            estimated_features.get('energy', 0.5),
            estimated_features.get('valence', 0.5),
            estimated_features.get('danceability', 0.5),
            estimated_features.get('acousticness', 0.3),
            estimated_features.get('instrumentalness', 0.1),
            estimated_features.get('tempo', 120) / 200.0,  # Normalize
            (estimated_features.get('loudness', -8) + 60) / 60.0  # Normalize
        ])
        
        # Track metadata features
        features.extend([
            track.get('popularity', 0) / 100.0,
            track.get('relevance_score', 0) / 100.0,
            len(track.get('name', '')) / 50.0,  # Title length normalized
            1.0 if track.get('preview_url') else 0.0,
            1.0 if track.get('explicit') else 0.0
        ])
        
        # Source features (one-hot)
        sources = ['deezer', 'itunes', 'lastfm', 'musicbrainz', 'audiodb']
        source = track.get('source', 'unknown')
        features.extend([1.0 if source == s else 0.0 for s in sources])
        
        # Genre/tag features
        tags = track.get('lastfm_tags', [])
        common_genres = ['rock', 'pop', 'electronic', 'jazz', 'classical', 'hip-hop', 'country', 'folk']
        for genre in common_genres:
            features.append(1.0 if any(genre.lower() in tag.lower() for tag in tags) else 0.0)
        
        # Context features (if provided)
        if context:
            # Time-based features
            current_hour = datetime.now().hour
            features.extend([
                current_hour / 24.0,  # Normalized hour
                1.0 if 6 <= current_hour <= 12 else 0.0,  # Morning
                1.0 if 12 <= current_hour <= 18 else 0.0,  # Afternoon
                1.0 if 18 <= current_hour <= 24 else 0.0,  # Evening
                1.0 if 0 <= current_hour <= 6 else 0.0,   # Night
            ])
            
            # Mood context features
            mood_data = context.get('mood_analysis', {})
            features.extend([
                mood_data.get('intensity', 0.5),
                mood_data.get('valence', 0.0),
                mood_data.get('arousal', 0.5)
            ])
            
            # Musical context features
            musical_context = context.get('musical_context', {})
            features.extend([
                musical_context.get('energy_preference', 0.5),
                musical_context.get('familiarity_preference', 0.5)
            ])
        else:
            # Add zeros for missing context features
            features.extend([0.0] * 10)
        
        return np.array(features)
    
    def train_user_model(self, user_id: int) -> Dict:
        """Train or update user's personalized model"""
        
        try:
            # Get user's feedback data
            feedback_data = self.db_manager.get_user_feedback_with_context(user_id)
            
            if len(feedback_data) < self.config.min_training_samples:
                return {
                    'success': False,
                    'message': f'Need at least {self.config.min_training_samples} ratings',
                    'current_samples': len(feedback_data)
                }
            
            # Prepare training data
            X_features = []
            y_ratings = []
            
            for feedback in feedback_data:
                try:
                    # Reconstruct track and context from feedback
                    track_data = {
                        'name': feedback['track_name'],
                        'artist': feedback['artist'],
                        'estimated_features': json.loads(feedback.get('track_features', '{}')),
                        'lastfm_tags': json.loads(feedback.get('track_tags', '[]')),
                        'source': feedback.get('source', 'unknown'),
                        'popularity': feedback.get('popularity', 0),
                        'relevance_score': feedback.get('relevance_score', 0)
                    }
                    
                    context_data = json.loads(feedback.get('context_data', '{}'))
                    
                    # Extract features
                    features = self.extract_track_features(track_data, context_data)
                    
                    X_features.append(features)
                    y_ratings.append(feedback['rating'])
                    
                except Exception as e:
                    logger.warning(f"Failed to process feedback entry: {e}")
                    continue
            
            if len(X_features) < self.config.min_training_samples:
                return {
                    'success': False,
                    'message': 'Insufficient valid training samples'
                }
            
            X = np.array(X_features)
            y = np.array(y_ratings)
            
            # Split data
            if len(X) > 10:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
            else:
                X_train, X_test, y_train, y_test = X, X, y, y
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model (using Random Forest for better feature importance)
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            
            # Cross-validation score
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=min(3, len(X_train)))
            cv_score = np.mean(cv_scores)
            
            # Calculate accuracy (1 - normalized MAE)
            accuracy = max(0, 1 - mae / 4.0)  # Rating scale is 1-5
            
            # Store model
            user_model = {
                'model': model,
                'scaler': scaler,
                'feature_importance': model.feature_importances_,
                'performance': {
                    'mae': mae,
                    'rmse': rmse,
                    'accuracy': accuracy,
                    'cv_score': cv_score,
                    'training_samples': len(X_train),
                    'test_samples': len(X_test)
                },
                'trained_at': datetime.now().isoformat(),
                'model_version': '1.0'
            }
            
            self.user_models[user_id] = user_model
            
            # Save models
            self._save_models()
            
            # Update database
            self.db_manager.update_user_model_stats(user_id, {
                'model_accuracy': accuracy,
                'training_samples': len(X_train),
                'last_trained': datetime.now()
            })
            
            logger.info(f"Trained model for user {user_id}: MAE={mae:.3f}, Accuracy={accuracy:.3f}")
            
            return {
                'success': True,
                'accuracy': accuracy,
                'mae': mae,
                'rmse': rmse,
                'cv_score': cv_score,
                'training_samples': len(X_train),
                'message': 'Model trained successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to train model for user {user_id}: {e}")
            return {
                'success': False,
                'message': f'Training failed: {str(e)}'
            }
    
    def predict_user_rating(self, user_id: int, track: Dict, context: Dict = None) -> float:
        """Predict user rating for a track"""
        
        if user_id not in self.user_models:
            # Try to train model if we have enough data
            training_result = self.train_user_model(user_id)
            if not training_result['success']:
                return 3.0  # Default neutral rating
        
        try:
            user_model = self.user_models[user_id]
            model = user_model['model']
            scaler = user_model['scaler']
            
            # Extract features
            features = self.extract_track_features(track, context)
            features_scaled = scaler.transform(features.reshape(1, -1))
            
            # Predict rating
            predicted_rating = model.predict(features_scaled)[0]
            
            # Clamp to valid range
            predicted_rating = max(1.0, min(5.0, predicted_rating))
            
            return predicted_rating
            
        except Exception as e:
            logger.error(f"Prediction failed for user {user_id}: {e}")
            return 3.0
    
    def get_prediction_confidence(self, user_id: int, track: Dict) -> float:
        """Get confidence score for prediction"""
        
        if user_id not in self.user_models:
            return 0.0
        
        try:
            user_model = self.user_models[user_id]
            performance = user_model['performance']
            
            # Base confidence from model accuracy
            base_confidence = performance['accuracy']
            
            # Adjust based on training data amount
            training_samples = performance['training_samples']
            sample_confidence = min(1.0, training_samples / 50.0)  # Full confidence at 50+ samples
            
            # Combine confidences
            confidence = (base_confidence * 0.7) + (sample_confidence * 0.3)
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.0
    
    def get_user_insights(self, user_id: int) -> Dict:
        """Get insights about user's model and preferences"""
        
        if user_id not in self.user_models:
            feedback_count = self.db_manager.get_user_feedback_count(user_id)
            return {
                'model_exists': False,
                'training_samples': feedback_count,
                'model_accuracy': 0.0,
                'message': f'Need {self.config.min_training_samples - feedback_count} more ratings to create model'
            }
        
        user_model = self.user_models[user_id]
        performance = user_model['performance']
        
        # Get feature importance insights
        feature_names = self._get_feature_names()
        feature_importance = user_model['feature_importance']
        
        # Top important features
        top_features_idx = np.argsort(feature_importance)[-5:]
        top_features = [(feature_names[i], feature_importance[i]) for i in top_features_idx]
        
        # Get user preference patterns from database
        preference_patterns = self.db_manager.get_user_preference_patterns(user_id)
        
        insights = {
            'model_exists': True,
            'model_accuracy': performance['accuracy'],
            'training_samples': performance['training_samples'],
            'model_quality': self._get_model_quality_description(performance['accuracy']),
            'top_features': top_features,
            'preference_patterns': preference_patterns,
            'last_trained': user_model['trained_at'],
            'cv_score': performance['cv_score']
        }
        
        return insights
    
    def get_detailed_insights(self, user_id: int) -> Dict:
        """Get detailed insights for UI display"""
        
        basic_insights = self.get_user_insights(user_id)
        
        if not basic_insights['model_exists']:
            return basic_insights
        
        # Add more detailed analysis
        feedback_analysis = self.db_manager.get_user_feedback_analysis(user_id)
        temporal_patterns = self.db_manager.get_user_temporal_patterns(user_id)
        
        detailed_insights = basic_insights.copy()
        detailed_insights.update({
            'preferences': {
                'genres': feedback_analysis.get('top_genres', []),
                'artists': feedback_analysis.get('top_artists', []),
                'moods': feedback_analysis.get('preferred_moods', []),
                'energy_levels': feedback_analysis.get('energy_preferences', {})
            },
            'learning_progress': min(1.0, basic_insights['training_samples'] / 50.0),
            'temporal_patterns': temporal_patterns,
            'recommendation_stats': feedback_analysis.get('recommendation_stats', {})
        })
        
        return detailed_insights
    
    def get_performance_history(self, user_id: int) -> Dict:
        """Get performance metrics over time for charts"""
        
        if user_id not in self.user_models:
            return {'accuracy_history': [], 'feature_importance': {}}
        
        # Get historical performance data
        performance_history = self.db_manager.get_user_model_performance_history(user_id)
        
        # Get current feature importance
        user_model = self.user_models[user_id]
        feature_names = self._get_feature_names()
        feature_importance = dict(zip(feature_names, user_model['feature_importance']))
        
        # Sort by importance
        sorted_features = dict(sorted(feature_importance.items(), 
                                    key=lambda x: x[1], reverse=True)[:10])
        
        return {
            'accuracy_history': performance_history,
            'feature_importance': sorted_features
        }
    
    async def update_user_model(self, user_id: int) -> Dict:
        """Update user model with new feedback (async version)"""
        return self.train_user_model(user_id)
    
    def _get_feature_names(self) -> List[str]:
        """Get names of all features"""
        return [
            'energy', 'valence', 'danceability', 'acousticness', 'instrumentalness', 
            'tempo', 'loudness', 'popularity', 'relevance_score', 'title_length',
            'has_preview', 'explicit',
            'source_deezer', 'source_itunes', 'source_lastfm', 'source_musicbrainz', 'source_audiodb',
            'genre_rock', 'genre_pop', 'genre_electronic', 'genre_jazz', 'genre_classical', 
            'genre_hip_hop', 'genre_country', 'genre_folk',
            'hour_normalized', 'is_morning', 'is_afternoon', 'is_evening', 'is_night',
            'mood_intensity', 'mood_valence', 'mood_arousal',
            'energy_preference', 'familiarity_preference'
        ]
    
    def _get_model_quality_description(self, accuracy: float) -> str:
        """Get human-readable model quality description"""
        if accuracy >= 0.85:
            return "Excellent"
        elif accuracy >= 0.75:
            return "Good"
        elif accuracy >= 0.65:
            return "Fair"
        elif accuracy >= 0.55:
            return "Learning"
        else:
            return "Poor"
