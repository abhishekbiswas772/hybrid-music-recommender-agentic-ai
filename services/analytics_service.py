import pandas as pd
import sqlite3
from typing import Dict, List
import json

class AnalyticsService:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_temporal_patterns(self, user_id: int) -> Dict:
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                interactions_df = pd.read_sql_query('''
                    SELECT timestamp FROM interactions WHERE user_id = ?
                ''', 'sqlite:///'+self.db_path, params=(user_id,))
                
                if len(interactions_df) == 0:
                    return {}
                
                interactions_df['timestamp'] = pd.to_datetime(interactions_df['timestamp'])
                interactions_df['hour'] = interactions_df['timestamp'].dt.hour
                interactions_df['day_of_week'] = interactions_df['timestamp'].dt.day_name()
                hourly_patterns = interactions_df['hour'].value_counts().to_dict()
                daily_patterns = interactions_df['day_of_week'].value_counts().to_dict()
                peak_hour = interactions_df['hour'].mode()[0] if len(interactions_df) > 0 else 12
                peak_day = interactions_df['day_of_week'].mode()[0] if len(interactions_df) > 0 else 'Monday'
                
                return {
                    'hourly_patterns': hourly_patterns,
                    'daily_patterns': daily_patterns,
                    'peak_hour': peak_hour,
                    'peak_day': peak_day,
                    'total_sessions': len(interactions_df)
                }
                
        except Exception as e:
            print(f"Error getting temporal patterns: {e}")
            return {}
    
    def get_music_discovery_trends(self, user_id: int) -> Dict:
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                feedback_df = pd.read_sql_query('''
                    SELECT rating, timestamp, track_tags, artist 
                    FROM feedback WHERE user_id = ?
                    ORDER BY timestamp
                ''', 'sqlite:///'+self.db_path, params=(user_id,))
                
                if len(feedback_df) == 0:
                    return {}
                
                feedback_df['timestamp'] = pd.to_datetime(feedback_df['timestamp'])
                total_artists = feedback_df['artist'].nunique()
                total_ratings = len(feedback_df)
                all_genres = []
                for tags_json in feedback_df['track_tags'].dropna():
                    try:
                        tags = json.loads(tags_json)
                        all_genres.extend(tags[:3])
                    except:
                        continue
                
                unique_genres = len(set(all_genres))
                feedback_df['week'] = feedback_df['timestamp'].dt.isocalendar().week
                weekly_avg_rating = feedback_df.groupby('week')['rating'].mean()
                feedback_df['cumulative_artists'] = feedback_df.groupby('artist').cumcount() == 0
                discovery_rate = feedback_df['cumulative_artists'].cumsum()
                
                return {
                    'total_artists_discovered': total_artists,
                    'unique_genres_explored': unique_genres,
                    'average_exploration_rating': feedback_df['rating'].mean(),
                    'discovery_rate_trend': discovery_rate.tolist()[-10:],  # Last 10 data points
                    'weekly_satisfaction': weekly_avg_rating.to_dict()
                }
                
        except Exception as e:
            print(f"Error getting discovery trends: {e}")
            return {}
    
    def generate_listening_insights(self, user_id: int) -> List[str]:
        insights = []
        try:
            temporal_patterns = self.get_temporal_patterns(user_id)
            discovery_trends = self.get_music_discovery_trends(user_id)
            if 'peak_hour' in temporal_patterns:
                peak_hour = temporal_patterns['peak_hour']
                if 6 <= peak_hour <= 12:
                    insights.append(f"🌅 You're a morning music lover! Most active at {peak_hour}:00")
                elif 18 <= peak_hour <= 23:
                    insights.append(f"🌆 Evening vibes! You discover most music at {peak_hour}:00")
                elif 0 <= peak_hour <= 5:
                    insights.append(f"🌙 Night owl! Your peak music time is {peak_hour}:00")
            
            if 'total_artists_discovered' in discovery_trends:
                artists_count = discovery_trends['total_artists_discovered']
                if artists_count > 50:
                    insights.append(f"🎨 Music explorer! You've discovered {artists_count} different artists")
                elif artists_count > 20:
                    insights.append(f"🔍 Good diversity! {artists_count} artists in your collection")

            if 'unique_genres_explored' in discovery_trends:
                genres_count = discovery_trends['unique_genres_explored']
                if genres_count > 20:
                    insights.append(f"🌈 Genre chameleon! You explore {genres_count} different styles")
                elif genres_count < 5:
                    insights.append("🎯 Focused taste! You know what you like")

            if 'average_exploration_rating' in discovery_trends:
                avg_rating = discovery_trends['average_exploration_rating']
                if avg_rating > 4.0:
                    insights.append(f"😊 High satisfaction! You rate tracks {avg_rating:.1f}/5 on average")
                elif avg_rating < 3.0:
                    insights.append("🔍 Room for improvement! Let's find music you'll love more")
            
            if not insights:
                insights.append("🎵 Keep rating tracks to unlock personalized insights!")
            
            return insights
            
        except Exception as e:
            print(f"Error generating insights: {e}")
            return ["🎵 Rate more tracks to see personalized insights!"]