# database/manager.py - Fixed Database Manager
import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

class DatabaseManager:
    """Enhanced database manager with RL-specific operations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # Ensure the directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"Created directory: {db_dir}")
        
        # Ensure the file can be created
        try:
            # Test if we can create/access the database file
            Path(self.db_path).touch(exist_ok=True)
        except Exception as e:
            print(f"Error creating database file: {e}")
            # Fallback to current directory
            self.db_path = "music_app.db"
            print(f"Using fallback database path: {self.db_path}")
        
        self.init_database()
    
    def init_database(self):
        """Initialize database with all required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Enable foreign keys
                cursor.execute("PRAGMA foreign_keys = ON")
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE,
                        full_name TEXT,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        preferences TEXT DEFAULT '{}',
                        settings TEXT DEFAULT '{}'
                    )
                ''')
                
                # Interactions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        query TEXT NOT NULL,
                        enhanced_query TEXT,
                        recommendations TEXT,
                        mood_analysis TEXT,
                        musical_context TEXT,
                        rl_enhanced BOOLEAN DEFAULT FALSE,
                        hybrid_score REAL,
                        processing_time_ms INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Enhanced feedback table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        interaction_id INTEGER,
                        track_id TEXT NOT NULL,
                        track_name TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        album TEXT,
                        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                        predicted_rating REAL,
                        rl_confidence REAL,
                        feedback_text TEXT,
                        track_features TEXT,
                        track_tags TEXT,
                        context_data TEXT,
                        source TEXT,
                        popularity INTEGER,
                        relevance_score REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (interaction_id) REFERENCES interactions (id)
                    )
                ''')
                
                # User model performance tracking
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_model_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        model_accuracy REAL,
                        mae REAL,
                        rmse REAL,
                        cv_score REAL,
                        training_samples INTEGER,
                        feature_importance TEXT,
                        model_version TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Create indexes
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_interactions_user_timestamp ON interactions(user_id, timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_feedback_user_rating ON feedback(user_id, rating)",
                    "CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_model_performance_user ON user_model_performance(user_id)"
                ]
                
                for index in indexes:
                    cursor.execute(index)
                
                conn.commit()
                print(f"✅ Database initialized successfully at: {self.db_path}")
                
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            raise
    
    def get_user_feedback_with_context(self, user_id: int) -> List[Dict]:
        """Get user feedback with full context for RL training"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT f.*, i.mood_analysis, i.musical_context
                    FROM feedback f
                    LEFT JOIN interactions i ON f.interaction_id = i.id
                    WHERE f.user_id = ?
                    ORDER BY f.timestamp DESC
                '''
                
                cursor.execute(query, (user_id,))
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"Error getting user feedback: {e}")
            return []
    
    def get_user_feedback_count(self, user_id: int) -> int:
        """Get count of feedback entries for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM feedback WHERE user_id = ?", (user_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting feedback count: {e}")
            return 0
    
    def update_user_model_stats(self, user_id: int, stats: Dict):
        """Update user model performance statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO user_model_performance 
                    (user_id, model_accuracy, training_samples, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (
                    user_id,
                    stats.get('model_accuracy', 0),
                    stats.get('training_samples', 0),
                    datetime.now()
                ))
                
                conn.commit()
        except Exception as e:
            print(f"Error updating model stats: {e}")
    
    def get_user_preference_patterns(self, user_id: int) -> Dict:
        """Get user preference patterns from feedback data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                
                # Get high-rated tracks
                high_rated_df = pd.read_sql_query('''
                    SELECT artist, track_tags, rating, track_features
                    FROM feedback 
                    WHERE user_id = ? AND rating >= 4
                ''', 'sqlite:///'+self.db_path, params=(user_id,))
                
                patterns = {}
                
                if len(high_rated_df) > 0:
                    # Top artists
                    patterns['preferred_artists'] = high_rated_df['artist'].value_counts().head(5).index.tolist()
                    
                    # Extract genres from tags
                    all_tags = []
                    for tags_json in high_rated_df['track_tags'].dropna():
                        try:
                            if tags_json:  # Check if not empty
                                tags = json.loads(tags_json)
                                all_tags.extend(tags)
                        except (json.JSONDecodeError, TypeError):
                            continue
                    
                    if all_tags:
                        tag_counts = pd.Series(all_tags).value_counts()
                        patterns['preferred_genres'] = tag_counts.head(5).index.tolist()
                    
                    # Average energy preference
                    energy_values = []
                    for features_json in high_rated_df['track_features'].dropna():
                        try:
                            if features_json:  # Check if not empty
                                features = json.loads(features_json)
                                energy_values.append(features.get('energy', 0.5))
                        except (json.JSONDecodeError, TypeError):
                            continue
                    
                    if energy_values:
                        patterns['average_energy'] = np.mean(energy_values)
                
                return patterns
                
        except Exception as e:
            print(f"Error getting preference patterns: {e}")
            return {}
    
    def get_user_feedback_analysis(self, user_id: int) -> Dict:
        """Get comprehensive feedback analysis"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                feedback_df = pd.read_sql_query('''
                    SELECT * FROM feedback WHERE user_id = ?
                ''', 'sqlite:///'+self.db_path, params=(user_id,))
                
                if len(feedback_df) == 0:
                    return {}
                
                analysis = {}
                
                # Rating distribution
                analysis['rating_distribution'] = feedback_df['rating'].value_counts().to_dict()
                analysis['average_rating'] = feedback_df['rating'].mean()
                
                # Top artists and genres from high ratings
                high_rated = feedback_df[feedback_df['rating'] >= 4]
                
                if len(high_rated) > 0:
                    analysis['top_artists'] = high_rated['artist'].value_counts().head(5).to_dict()
                    
                    # Extract genres
                    all_genres = []
                    for tags_json in high_rated['track_tags'].dropna():
                        try:
                            if tags_json:  # Check if not empty
                                tags = json.loads(tags_json)
                                all_genres.extend(tags[:3])  # Top 3 tags per track
                        except (json.JSONDecodeError, TypeError):
                            continue
                    
                    if all_genres:
                        genre_counts = pd.Series(all_genres).value_counts()
                        analysis['top_genres'] = genre_counts.head(5).to_dict()
                
                # Recommendation stats
                analysis['recommendation_stats'] = {
                    'total_ratings': len(feedback_df),
                    'positive_ratings': len(feedback_df[feedback_df['rating'] >= 4]),
                    'negative_ratings': len(feedback_df[feedback_df['rating'] <= 2]),
                    'rating_variance': feedback_df['rating'].var()
                }
                
                return analysis
                
        except Exception as e:
            print(f"Error getting feedback analysis: {e}")
            return {}
    
    def get_user_temporal_patterns(self, user_id: int) -> Dict:
        """Get user's temporal listening patterns"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                interactions_df = pd.read_sql_query('''
                    SELECT timestamp FROM interactions WHERE user_id = ?
                ''', 'sqlite:///'+self.db_path, params=(user_id,))
                
                if len(interactions_df) == 0:
                    return {}
                
                interactions_df['timestamp'] = pd.to_datetime(interactions_df['timestamp'])
                interactions_df['hour'] = interactions_df['timestamp'].dt.hour
                interactions_df['day_of_week'] = interactions_df['timestamp'].dt.day_name()
                
                patterns = {
                    'hourly_activity': interactions_df['hour'].value_counts().to_dict(),
                    'daily_activity': interactions_df['day_of_week'].value_counts().to_dict(),
                    'peak_hour': interactions_df['hour'].mode()[0] if len(interactions_df) > 0 else 12,
                    'peak_day': interactions_df['day_of_week'].mode()[0] if len(interactions_df) > 0 else 'Monday'
                }
                
                return patterns
                
        except Exception as e:
            print(f"Error getting temporal patterns: {e}")
            return {}
    
    def get_user_model_performance_history(self, user_id: int) -> List[Dict]:
        """Get historical model performance data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT model_accuracy, timestamp 
                    FROM user_model_performance 
                    WHERE user_id = ? 
                    ORDER BY timestamp
                ''', (user_id,))
                
                rows = cursor.fetchall()
                
                return [
                    {'accuracy': row[0], 'timestamp': row[1]} 
                    for row in rows
                ]
        except Exception as e:
            print(f"Error getting performance history: {e}")
            return []
    
    def log_interaction(self, interaction_data: Dict):
        """Log user interaction"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO interactions 
                    (user_id, query, enhanced_query, recommendations, mood_analysis, 
                     musical_context, rl_enhanced, hybrid_score, processing_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    interaction_data['user_id'],
                    interaction_data['query'],
                    interaction_data.get('enhanced_query'),
                    json.dumps(interaction_data.get('recommendations', [])),
                    json.dumps(interaction_data.get('mood_analysis', {})),
                    json.dumps(interaction_data.get('musical_context', {})),
                    interaction_data.get('rl_enhanced', False),
                    interaction_data.get('hybrid_score', 0),
                    interaction_data.get('processing_time_ms', 0)
                ))
                
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error logging interaction: {e}")
            return None
    
    def log_feedback(self, feedback_data: Dict):
        """Log user feedback"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO feedback 
                    (user_id, interaction_id, track_id, track_name, artist, rating, 
                     predicted_rating, rl_confidence, feedback_text, track_features, 
                     track_tags, context_data, source, popularity, relevance_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    feedback_data['user_id'],
                    feedback_data.get('interaction_id'),
                    feedback_data['track_id'],
                    feedback_data['track_name'],
                    feedback_data['artist'],
                    feedback_data['rating'],
                    feedback_data.get('predicted_rating'),
                    feedback_data.get('rl_confidence'),
                    feedback_data.get('feedback_text'),
                    json.dumps(feedback_data.get('track_features', {})),
                    json.dumps(feedback_data.get('track_tags', [])),
                    json.dumps(feedback_data.get('context_data', {})),
                    feedback_data.get('source'),
                    feedback_data.get('popularity'),
                    feedback_data.get('relevance_score')
                ))
                
                conn.commit()
        except Exception as e:
            print(f"Error logging feedback: {e}")
    
    def get_user_data(self, user_id: int) -> Dict:
        """Get basic user data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                row = cursor.fetchone()
                
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return {}
        except Exception as e:
            print(f"Error getting user data: {e}")
            return {}
    
    def get_recent_interactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent user interactions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM interactions 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"Error getting recent interactions: {e}")
            return []
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Basic stats
                cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id = ?', (user_id,))
                total_interactions = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM feedback WHERE user_id = ?', (user_id,))
                total_feedback = cursor.fetchone()[0]
                
                cursor.execute('SELECT AVG(rating) FROM feedback WHERE user_id = ?', (user_id,))
                avg_rating_result = cursor.fetchone()
                average_rating = avg_rating_result[0] if avg_rating_result[0] else 0
                
                # Recent high-rated tracks
                cursor.execute('''
                    SELECT track_name, artist, rating, timestamp
                    FROM feedback 
                    WHERE user_id = ? AND rating >= 4
                    ORDER BY timestamp DESC
                    LIMIT 5
                ''', (user_id,))
                
                recent_high_rated = [
                    {
                        'track_name': row[0],
                        'artist': row[1],
                        'rating': row[2],
                        'timestamp': row[3]
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    'total_interactions': total_interactions,
                    'total_feedback': total_feedback,
                    'average_rating': average_rating,
                    'recent_high_rated': recent_high_rated
                }
                
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {
                'total_interactions': 0,
                'total_feedback': 0,
                'average_rating': 0,
                'recent_high_rated': []
            }
        
    def get_feedback_patterns(self, user_id: int) -> Dict:
        """Get user feedback patterns"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                feedback_df = pd.read_sql_query('''
                    SELECT rating, track_tags, artist, timestamp
                    FROM feedback 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                ''', 'sqlite:///'+self.db_path, params=(user_id,))
                
                if len(feedback_df) == 0:
                    return {}
                
                patterns = {
                    'preferred_moods': [],
                    'avg_rating': feedback_df['rating'].mean(),
                    'total_ratings': len(feedback_df)
                }
                
                # Extract mood patterns from high-rated tracks
                high_rated = feedback_df[feedback_df['rating'] >= 4]
                if len(high_rated) > 0:
                    all_tags = []
                    for tags_json in high_rated['track_tags'].dropna():
                        try:
                            if tags_json:
                                tags = json.loads(tags_json)
                                all_tags.extend(tags[:2])
                        except:
                            continue
                    
                    if all_tags:
                        from collections import Counter
                        mood_counts = Counter(all_tags)
                        patterns['preferred_moods'] = list(mood_counts.keys())[:5]
                
                return patterns
                
        except Exception as e:
            print(f"Error getting feedback patterns: {e}")
            return {}