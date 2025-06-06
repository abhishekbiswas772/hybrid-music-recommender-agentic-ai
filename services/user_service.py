import hashlib
import sqlite3
from typing import Dict, Optional
from datetime import datetime
import json

class UserService:
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_user(self, username: str, email: str, password: str, full_name: str = None) -> bool:
        try:
            password_hash = self._hash_password(password)
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO users (username, email, full_name, password_hash, preferences, settings)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    username,
                    email,
                    full_name,
                    password_hash,
                    json.dumps({}), 
                    json.dumps({   
                        'theme': 'dark',
                        'email_notifications': True,
                        'ai_learning_enabled': True
                    })
                ))
                
                conn.commit()
                return True
                
        except sqlite3.IntegrityError:
            return False  # Username or email already exists
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def authenticate(self, username: str, password: str) -> bool:
        try:
            password_hash = self._hash_password(password)
            
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM users 
                    WHERE username = ? AND password_hash = ?
                ''', (username, password_hash))
                
                result = cursor.fetchone()
                
                if result:
                    # Update last login
                    cursor.execute('''
                        UPDATE users SET last_login = ? WHERE id = ?
                    ''', (datetime.now(), result[0]))
                    conn.commit()
                    
                    return True
                
                return False
                
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user data by username"""
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, username, email, full_name, created_at, last_login, preferences, settings
                    FROM users WHERE username = ?
                ''', (username,))
                
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'username': row[1],
                        'email': row[2],
                        'full_name': row[3],
                        'created_at': row[4],
                        'last_login': row[5],
                        'preferences': json.loads(row[6]) if row[6] else {},
                        'settings': json.loads(row[7]) if row[7] else {}
                    }
                
                return None
                
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, username, email, full_name, created_at, last_login, preferences, settings
                    FROM users WHERE id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'username': row[1],
                        'email': row[2],
                        'full_name': row[3],
                        'created_at': row[4],
                        'last_login': row[5],
                        'preferences': json.loads(row[6]) if row[6] else {},
                        'settings': json.loads(row[7]) if row[7] else {}
                    }
                
                return None
                
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def update_user_preferences(self, user_id: int, preferences: Dict) -> bool:
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE users SET preferences = ? WHERE id = ?
                ''', (json.dumps(preferences), user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error updating preferences: {e}")
            return False
    
    def update_user_settings(self, user_id: int, settings: Dict) -> bool:
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE users SET settings = ? WHERE id = ?
                ''', (json.dumps(settings), user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error updating settings: {e}")
            return False
    
    def get_user_stats(self, user_id: int) -> Dict:
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM interactions WHERE user_id = ?', (user_id,))
                total_interactions = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM feedback WHERE user_id = ?', (user_id,))
                total_feedback = cursor.fetchone()[0]
                
                cursor.execute('SELECT AVG(rating) FROM feedback WHERE user_id = ?', (user_id,))
                avg_rating_result = cursor.fetchone()
                average_rating = avg_rating_result[0] if avg_rating_result[0] else 0
                personalization_level = min(1.0, total_feedback / 20.0)
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
                    'personalization_level': personalization_level,
                    'recent_high_rated': recent_high_rated
                }
                
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {
                'total_interactions': 0,
                'total_feedback': 0,
                'average_rating': 0,
                'personalization_level': 0,
                'recent_high_rated': []
            }
    
    def delete_user(self, user_id: int) -> bool:
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM feedback WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM interactions WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM user_model_performance WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    def _hash_password(self, password: str) -> str:
        salt = "music_curator_salt"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            old_hash = self._hash_password(old_password)
            
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM users WHERE id = ? AND password_hash = ?
                ''', (user_id, old_hash))
                
                if not cursor.fetchone():
                    return False 
                
                new_hash = self._hash_password(new_password)
                cursor.execute('''
                    UPDATE users SET password_hash = ? WHERE id = ?
                ''', (new_hash, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error changing password: {e}")
            return False