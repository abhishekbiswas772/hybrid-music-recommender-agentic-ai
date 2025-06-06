from typing import Dict, List, Tuple
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
from io import BytesIO

class AnalyticsPage:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def show_analytics_page(self, user: Dict, db_manager):
        st.markdown("### 📊 Your Music Analytics Dashboard")
        analytics_data = self._get_comprehensive_analytics(user['id'])
        
        if analytics_data['total_interactions'] == 0:
            self._show_empty_state()
            return
        
        self._show_overview_metrics(analytics_data)
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📈 Activity Trends",
            "🎭 Music Preferences", 
            "⭐ Rating Analysis",
            "🤖 AI Performance",
            "📊 Listening Patterns",
            "📄 Export & Reports"
        ])
        
        with tab1:
            self._show_activity_trends(analytics_data)
        
        with tab2:
            self._show_music_preferences(analytics_data)
        
        with tab3:
            self._show_rating_analysis(analytics_data)
        
        with tab4:
            self._show_ai_performance(analytics_data)
        
        with tab5:
            self._show_listening_patterns(analytics_data)
        
        with tab6:
            self._show_export_reports(user, analytics_data)
    
    def _get_comprehensive_analytics(self, user_id: int) -> Dict:
        interactions_df = pd.read_sql_query(
            'SELECT * FROM interactions WHERE user_id = ? ORDER BY timestamp',
            'sqlite:///'+self.db_manager.db_path, params=(user_id,)
        )
        
        feedback_df = pd.read_sql_query(
            'SELECT * FROM feedback WHERE user_id = ? ORDER BY timestamp',
           'sqlite:///'+self.db_manager.db_path, params=(user_id,)
        )
        
        model_performance_df = pd.read_sql_query(
            'SELECT * FROM user_model_performance WHERE user_id = ? ORDER BY timestamp',
            'sqlite:///'+self.db_manager.db_path, params=(user_id,)
        )
        

        total_interactions = len(interactions_df)
        total_feedback = len(feedback_df)
        avg_rating = feedback_df['rating'].mean() if len(feedback_df) > 0 else 0

        recent_date = datetime.now() - timedelta(days=30)
        recent_interactions = len(interactions_df[
            pd.to_datetime(interactions_df['timestamp']) >= recent_date
        ]) if len(interactions_df) > 0 else 0
        
        recent_feedback = len(feedback_df[
            pd.to_datetime(feedback_df['timestamp']) >= recent_date
        ]) if len(feedback_df) > 0 else 0
        
        return {
            'total_interactions': total_interactions,
            'total_feedback': total_feedback,
            'average_rating': avg_rating,
            'recent_interactions': recent_interactions,
            'recent_feedback': recent_feedback,
            'interactions_df': interactions_df,
            'feedback_df': feedback_df,
            'model_performance_df': model_performance_df
        }
    
    def _show_empty_state(self):
        st.info("""
        🎵 **Start Your Music Journey!**
        
        You haven't used the music recommender yet. Start by:
        1. Making your first music query
        2. Rating the recommended tracks
        3. Let the AI learn your preferences
        
        Come back here to see detailed analytics of your music taste!
        """)
    
    def _show_overview_metrics(self, data: Dict):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Queries",
                data['total_interactions'],
                delta=data['recent_interactions'],
                delta_color="normal",
                help="Total music recommendation requests"
            )
        
        with col2:
            st.metric(
                "Tracks Rated",
                data['total_feedback'],
                delta=data['recent_feedback'],
                delta_color="normal",
                help="Number of tracks you've rated"
            )
        
        with col3:
            avg_rating = data['average_rating']
            if avg_rating > 0:
                st.metric(
                    "Average Rating",
                    f"{avg_rating:.1f}/5",
                    help="Your average rating across all tracks"
                )
            else:
                st.metric("Average Rating", "No ratings yet")
        
        with col4:
            if data['total_feedback'] >= 5:
                progress = min(100, (data['total_feedback'] / 50) * 100)
                st.metric(
                    "AI Learning",
                    f"{progress:.0f}%",
                    help="How well the AI knows your preferences"
                )
            else:
                needed = 5 - data['total_feedback']
                st.metric(
                    "AI Learning",
                    f"Need {needed} more ratings",
                    help="Rate more tracks to activate AI learning"
                )
    
    def _show_activity_trends(self, data: Dict):
        interactions_df = data['interactions_df']
        feedback_df = data['feedback_df']
        
        if len(interactions_df) == 0:
            st.info("No activity data available yet.")
            return

        interactions_df['timestamp'] = pd.to_datetime(interactions_df['timestamp'])
        interactions_df['date'] = interactions_df['timestamp'].dt.date
        interactions_df['hour'] = interactions_df['timestamp'].dt.hour
        interactions_df['day_name'] = interactions_df['timestamp'].dt.day_name()
        daily_activity = interactions_df.groupby('date').size().reset_index(name='queries')
        fig1 = px.line(
            daily_activity, 
            x='date', 
            y='queries',
            title="Daily Query Activity",
            labels={'queries': 'Number of Queries', 'date': 'Date'}
        )
        fig1.update_layout(showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)
        col1, col2 = st.columns(2)
        
        with col1:
            hourly_activity = interactions_df.groupby('hour').size().reset_index(name='queries')
            
            fig2 = px.bar(
                hourly_activity,
                x='hour',
                y='queries',
                title="Activity by Hour of Day",
                labels={'hour': 'Hour', 'queries': 'Queries'}
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        with col2:
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            daily_pattern = interactions_df.groupby('day_name').size().reset_index(name='queries')
            daily_pattern['day_name'] = pd.Categorical(
                daily_pattern['day_name'], 
                categories=day_order, 
                ordered=True
            )
            daily_pattern = daily_pattern.sort_values('day_name')
            fig3 = px.bar(
                daily_pattern,
                x='day_name',
                y='queries',
                title="Activity by Day of Week",
                labels={'day_name': 'Day', 'queries': 'Queries'}
            )
            st.plotly_chart(fig3, use_container_width=True)
        
        if len(interactions_df) > 5:
            peak_hour = interactions_df['hour'].mode()[0]
            peak_day = interactions_df['day_name'].mode()[0]
            st.info(f"""
            📊 **Activity Insights:**
            - Most active hour: {peak_hour}:00
            - Most active day: {peak_day}
            - Total active days: {len(daily_activity)}
            """)
    
    def _show_music_preferences(self, data: Dict):
        feedback_df = data['feedback_df']
        if len(feedback_df) == 0:
            st.info("Rate some tracks to see your music preferences!")
            return

        genre_data = self._extract_genre_data(feedback_df)
        if genre_data:
            col1, col2 = st.columns(2)
            
            with col1:
                # Top genres
                genre_df = pd.DataFrame(list(genre_data.items()), columns=['Genre', 'Count'])
                genre_df = genre_df.sort_values('Count', ascending=False).head(10)
                
                fig1 = px.pie(
                    genre_df,
                    values='Count',
                    names='Genre',
                    title="Your Top Genres"
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                genre_ratings = self._get_genre_ratings(feedback_df)
                if genre_ratings:
                    genre_rating_df = pd.DataFrame(
                        list(genre_ratings.items()),
                        columns=['Genre', 'Average Rating']
                    ).sort_values('Average Rating', ascending=False).head(10)
                    
                    fig2 = px.bar(
                        genre_rating_df,
                        x='Average Rating',
                        y='Genre',
                        orientation='h',
                        title="Genre Ratings",
                        labels={'Average Rating': 'Average Rating (1-5)'}
                    )
                    st.plotly_chart(fig2, use_container_width=True)

        artist_data = feedback_df.groupby('artist').agg({
            'rating': ['count', 'mean']
        }).round(2)
        
        artist_data.columns = ['Tracks Rated', 'Average Rating']
        artist_data = artist_data[artist_data['Tracks Rated'] >= 2].sort_values(
            'Average Rating', ascending=False
        ).head(10)
        
        if len(artist_data) > 0:
            st.markdown("#### 🎤 Your Favorite Artists")
            
            fig3 = px.scatter(
                artist_data.reset_index(),
                x='Tracks Rated',
                y='Average Rating',
                hover_name='artist',
                title="Artist Ratings vs Number of Tracks",
                labels={
                    'Tracks Rated': 'Number of Tracks Rated',
                    'Average Rating': 'Average Rating'
                }
            )
            st.plotly_chart(fig3, use_container_width=True)
            st.dataframe(
                artist_data,
                use_container_width=True,
                column_config={
                    "Tracks Rated": st.column_config.NumberColumn(format="%d"),
                    "Average Rating": st.column_config.NumberColumn(format="%.1f")
                }
            )
    
    def _show_rating_analysis(self, data: Dict):
        feedback_df = data['feedback_df']
        
        if len(feedback_df) == 0:
            st.info("No ratings available yet.")
            return
        
        rating_counts = feedback_df['rating'].value_counts().sort_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                x=rating_counts.index,
                y=rating_counts.values,
                title="Rating Distribution",
                labels={'x': 'Rating (1-5)', 'y': 'Number of Tracks'}
            )
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            feedback_df['timestamp'] = pd.to_datetime(feedback_df['timestamp'])
            feedback_df['date'] = feedback_df['timestamp'].dt.date
            
            daily_ratings = feedback_df.groupby('date')['rating'].mean().reset_index()
            
            fig2 = px.line(
                daily_ratings,
                x='date',
                y='rating',
                title="Average Rating Over Time",
                labels={'rating': 'Average Daily Rating', 'date': 'Date'}
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown("#### 📊 Rating Insights")
        
        insights_col1, insights_col2, insights_col3 = st.columns(3)
        
        with insights_col1:
            high_rated = len(feedback_df[feedback_df['rating'] >= 4])
            total_rated = len(feedback_df)
            satisfaction_rate = (high_rated / total_rated * 100) if total_rated > 0 else 0
            
            st.metric("Satisfaction Rate", f"{satisfaction_rate:.1f}%", 
                     help="Percentage of tracks rated 4+ stars")
        
        with insights_col2:
            rating_variance = feedback_df['rating'].var()
            consistency = "High" if rating_variance < 1 else "Medium" if rating_variance < 2 else "Low"
            
            st.metric("Rating Consistency", consistency,
                     help="How consistent your ratings are")
        
        with insights_col3:
            if len(feedback_df) >= 10:
                recent_avg = feedback_df.tail(10)['rating'].mean()
                overall_avg = feedback_df['rating'].mean()
                trend = "↗️ Improving" if recent_avg > overall_avg + 0.2 else "↘️ Declining" if recent_avg < overall_avg - 0.2 else "→ Stable"
                
                st.metric("Recent Trend", trend,
                         help="How your recent ratings compare to overall average")
    
    def _show_ai_performance(self, data: Dict):
        model_performance_df = data['model_performance_df']
        feedback_df = data['feedback_df']
        
        if len(model_performance_df) == 0:
            st.info("AI model not trained yet. Rate more tracks to enable AI performance tracking.")
            return
        latest_performance = model_performance_df.iloc[-1]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            accuracy = latest_performance['model_accuracy'] * 100
            st.metric("Prediction Accuracy", f"{accuracy:.1f}%")
        
        with col2:
            mae = latest_performance['mae']
            st.metric("Mean Absolute Error", f"{mae:.2f}")
        
        with col3:
            training_samples = latest_performance['training_samples']
            st.metric("Training Data", f"{training_samples} tracks")
        
        with col4:
            cv_score = latest_performance.get('cv_score', 0) * 100
            st.metric("Cross-Validation Score", f"{cv_score:.1f}%")
        
        if len(model_performance_df) > 1:
            model_performance_df['timestamp'] = pd.to_datetime(model_performance_df['timestamp'])
            
            fig1 = px.line(
                model_performance_df,
                x='timestamp',
                y='model_accuracy',
                title="AI Model Accuracy Over Time",
                labels={'model_accuracy': 'Accuracy', 'timestamp': 'Date'}
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        feedback_with_predictions = feedback_df[feedback_df['predicted_rating'].notna()]
        if len(feedback_with_predictions) > 5:
            fig2 = px.scatter(
                feedback_with_predictions,
                x='predicted_rating',
                y='rating',
                title="Predicted vs Actual Ratings",
                labels={'predicted_rating': 'AI Predicted Rating', 'rating': 'Your Actual Rating'}
            )
            
            fig2.add_trace(go.Scatter(
                x=[1, 5], y=[1, 5],
                mode='lines',
                name='Perfect Prediction',
                line=dict(dash='dash', color='red')
            ))
            
            st.plotly_chart(fig2, use_container_width=True)
            mae_actual = abs(feedback_with_predictions['rating'] - feedback_with_predictions['predicted_rating']).mean()
            st.info(f"🤖 **AI Insights:** On average, the AI predictions are within {mae_actual:.2f} stars of your actual ratings.")
    
    def _show_listening_patterns(self, data: Dict):
        interactions_df = data['interactions_df']
        feedback_df = data['feedback_df']
        
        if len(interactions_df) == 0:
            st.info("No listening pattern data available yet.")
            return
        
        mood_data = self._extract_mood_data(interactions_df)
        
        if mood_data:
            col1, col2 = st.columns(2)
            
            with col1:
                mood_counts = pd.Series(mood_data).value_counts()
                
                fig1 = px.pie(
                    values=mood_counts.values,
                    names=mood_counts.index,
                    title="Mood Distribution"
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                interactions_df['mood'] = mood_data
                interactions_df['hour'] = pd.to_datetime(interactions_df['timestamp']).dt.hour
                
                mood_by_hour = interactions_df.groupby(['hour', 'mood']).size().unstack(fill_value=0)
                
                fig2 = px.bar(
                    mood_by_hour.reset_index(),
                    x='hour',
                    y=mood_by_hour.columns.tolist(),
                    title="Mood by Hour of Day",
                    labels={'hour': 'Hour of Day'}
                )
                st.plotly_chart(fig2, use_container_width=True)
        
        if len(interactions_df) > 0:
            st.markdown("#### 🔍 Query Analysis")
            interactions_df['query_length'] = interactions_df['query'].str.len()
            avg_query_length = interactions_df['query_length'].mean()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Average Query Length", f"{avg_query_length:.0f} characters")
                all_queries = ' '.join(interactions_df['query'].str.lower())
                common_words = self._get_common_words(all_queries)
                
                if common_words:
                    st.markdown("**Most Common Words:**")
                    for word, count in common_words[:10]:
                        st.write(f"• {word}: {count} times")
            
            with col2:
                fig3 = px.histogram(
                    interactions_df,
                    x='query_length',
                    title="Query Length Distribution",
                    labels={'query_length': 'Query Length (characters)'}
                )
                st.plotly_chart(fig3, use_container_width=True)
    
    def _show_export_reports(self, user: Dict, data: Dict):
        """Show export and reporting options"""
        
        st.markdown("#### 📄 Export Your Data")
        report_type = st.selectbox(
            "Select Report Type:",
            [
                "Complete Analytics Report",
                "Music Preferences Summary",
                "AI Performance Report",
                "Activity Timeline",
                "Custom Date Range Report"
            ]
        )
        
        if report_type == "Custom Date Range Report":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", 
                                         value=datetime.now().date() - timedelta(days=30))
            with col2:
                end_date = st.date_input("End Date", value=datetime.now().date())
        else:
            start_date = None
            end_date = None
        
        export_format = st.selectbox("Export Format:", ["Excel (.xlsx)", "CSV", "JSON"])
        if st.button("📥 Generate Report", type="primary"):
            with st.spinner("Generating report..."):
                if export_format == "Excel (.xlsx)":
                    report_data = self._generate_excel_report(
                        user, data, report_type, start_date, end_date
                    )
                    if report_data:
                        st.download_button(
                            label="📥 Download Excel Report",
                            data=report_data,
                            file_name=f"music_analytics_{user['username']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.success("Report generated successfully!")
                
                elif export_format == "CSV":
                    csv_data = self._generate_csv_report(user, data, report_type)
                    
                    st.download_button(
                        label="📥 Download CSV Report",
                        data=csv_data,
                        file_name=f"music_analytics_{user['username']}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                    st.success("CSV report generated!")
                
                elif export_format == "JSON":
                    json_data = self._generate_json_report(user, data, report_type)
                    
                    st.download_button(
                        label="📥 Download JSON Report",
                        data=json_data,
                        file_name=f"music_analytics_{user['username']}_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
                    st.success("JSON report generated!")

        if st.checkbox("Show Report Preview"):
            self._show_report_preview(user, data, report_type)
    
    def _generate_excel_report(self, user: Dict, data: Dict, report_type: str, 
                              start_date=None, end_date=None) -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BD',
                'border': 1
            })
            
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 16,
                'fg_color': '#4CAF50',
                'font_color': 'white'
            })
            
            summary_data = {
                'Metric': [
                    'User', 'Report Generated', 'Report Type', 'Total Queries',
                    'Total Ratings', 'Average Rating', 'Satisfaction Rate',
                    'AI Model Status', 'Most Active Day', 'Favorite Genre'
                ],
                'Value': [
                    user['username'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    report_type,
                    data['total_interactions'],
                    data['total_feedback'],
                    f"{data['average_rating']:.2f}" if data['average_rating'] > 0 else "No ratings",
                    f"{self._calculate_satisfaction_rate(data['feedback_df']):.1f}%" if len(data['feedback_df']) > 0 else "N/A",
                    "Active" if len(data['model_performance_df']) > 0 else "Not Trained",
                    self._get_most_active_day(data['interactions_df']),
                    self._get_top_genre(data['feedback_df'])
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
            worksheet = writer.sheets['Executive Summary']
            worksheet.write('A1', 'Music Analytics Report', title_format)
            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 30)

            if len(data['interactions_df']) > 0:
                activity_df = data['interactions_df'][['timestamp', 'query', 'rl_enhanced']].copy()
                activity_df['timestamp'] = pd.to_datetime(activity_df['timestamp'])
                activity_df.to_excel(writer, sheet_name='Activity Timeline', index=False)
            
            if len(data['feedback_df']) > 0:
                ratings_df = data['feedback_df'][[
                    'timestamp', 'track_name', 'artist', 'rating', 
                    'predicted_rating', 'feedback_text'
                ]].copy()
                ratings_df['timestamp'] = pd.to_datetime(ratings_df['timestamp'])
                ratings_df.to_excel(writer, sheet_name='Ratings History', index=False)
            
            if len(data['feedback_df']) > 0:
                artist_stats = data['feedback_df'].groupby('artist').agg({
                    'rating': ['count', 'mean']
                }).round(2)
                artist_stats.columns = ['Tracks Rated', 'Average Rating']
                artist_stats = artist_stats.sort_values('Average Rating', ascending=False)
                artist_stats.to_excel(writer, sheet_name='Artist Preferences')
                
                genre_data = self._extract_genre_data(data['feedback_df'])
                if genre_data:
                    genre_df = pd.DataFrame(
                        list(genre_data.items()), 
                        columns=['Genre', 'Count']
                    ).sort_values('Count', ascending=False)
                    
                    genre_df.to_excel(writer, sheet_name='Genre Preferences', index=False)
  
            if len(data['model_performance_df']) > 0:
                ai_performance = data['model_performance_df'][[
                    'timestamp', 'model_accuracy', 'mae', 'training_samples'
                ]].copy()
                ai_performance['timestamp'] = pd.to_datetime(ai_performance['timestamp'])
                ai_performance.to_excel(writer, sheet_name='AI Performance', index=False)
        
        return output.getvalue()
    
    def _generate_csv_report(self, user: Dict, data: Dict, report_type: str) -> str:
        if report_type == "Activity Timeline":
            df = data['interactions_df'][['timestamp', 'query', 'rl_enhanced']].copy()
        elif report_type == "Music Preferences Summary":
            df = data['feedback_df'][['timestamp', 'track_name', 'artist', 'rating']].copy()
        else:
            df = data['feedback_df'][['timestamp', 'track_name', 'artist', 'rating', 'feedback_text']].copy()
        
        return df.to_csv(index=False)
    
    def _generate_json_report(self, user: Dict, data: Dict, report_type: str) -> str:
        report_data = {
            'user': user['username'],
            'generated_at': datetime.now().isoformat(),
            'report_type': report_type,
            'summary': {
                'total_interactions': data['total_interactions'],
                'total_feedback': data['total_feedback'],
                'average_rating': data['average_rating']
            }
        }
        
        if report_type == "Complete Analytics Report":
            report_data['interactions'] = data['interactions_df'].to_dict('records')
            report_data['feedback'] = data['feedback_df'].to_dict('records')
            report_data['ai_performance'] = data['model_performance_df'].to_dict('records')
        
        return json.dumps(report_data, indent=2, default=str)
    
    def _show_report_preview(self, user: Dict, data: Dict, report_type: str):
        st.markdown("#### 📋 Report Preview")
        if report_type == "Complete Analytics Report":
            st.write("**This report will include:**")
            st.write("• Executive summary with key metrics")
            st.write("• Complete activity timeline")
            st.write("• All ratings and feedback")
            st.write("• Music preference analysis")
            st.write("• AI performance metrics")
            
        elif report_type == "Music Preferences Summary":
            st.write("**This report will include:**")
            st.write("• Top genres and artists")
            st.write("• Rating patterns")
            st.write("• Preference insights")
            
        if len(data['feedback_df']) > 0:
            st.markdown("**Sample Data:**")
            sample_df = data['feedback_df'][['track_name', 'artist', 'rating']].head(5)
            st.dataframe(sample_df, use_container_width=True)
    
    def _extract_genre_data(self, feedback_df: pd.DataFrame) -> Dict:
        genre_counts = {}
        
        for _, row in feedback_df.iterrows():
            try:
                tags = json.loads(row.get('track_tags', '[]'))
                for tag in tags[:3]:  # Top 3 tags per track
                    genre_counts[tag] = genre_counts.get(tag, 0) + 1
            except:
                continue
        
        return genre_counts
    
    def _get_genre_ratings(self, feedback_df: pd.DataFrame) -> Dict:
        genre_ratings = {}
        
        for _, row in feedback_df.iterrows():
            try:
                tags = json.loads(row.get('track_tags', '[]'))
                rating = row['rating']
                
                for tag in tags[:2]:  
                    if tag not in genre_ratings:
                        genre_ratings[tag] = []
                    genre_ratings[tag].append(rating)
            except:
                continue
        
        return {
            genre: sum(ratings) / len(ratings)
            for genre, ratings in genre_ratings.items()
            if len(ratings) >= 2  
        }
    
    def _extract_mood_data(self, interactions_df: pd.DataFrame) -> List:
        moods = []
        
        for _, row in interactions_df.iterrows():
            try:
                mood_analysis = json.loads(row.get('mood_analysis', '{}'))
                primary_emotion = mood_analysis.get('primary_emotion', 'unknown')
                moods.append(primary_emotion)
            except:
                moods.append('unknown')
        
        return moods
    
    def _get_common_words(self, text: str) -> List[Tuple[str, int]]:
        import re
        from collections import Counter
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'i', 'me', 'my', 'you', 'your', 'it', 'its', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'that', 'this', 'these', 'those'}
        words = re.findall(r'\b\w+\b', text.lower())
        words = [word for word in words if word not in stop_words and len(word) > 2]
        
        return Counter(words).most_common(15)
    
    def _calculate_satisfaction_rate(self, feedback_df: pd.DataFrame) -> float:
        if len(feedback_df) == 0:
            return 0.0
        
        high_rated = len(feedback_df[feedback_df['rating'] >= 4])
        return (high_rated / len(feedback_df)) * 100
    
    def _get_most_active_day(self, interactions_df: pd.DataFrame) -> str:
        if len(interactions_df) == 0:
            return "No data"
        
        interactions_df = interactions_df.copy()
        interactions_df['timestamp'] = pd.to_datetime(interactions_df['timestamp'])
        interactions_df['day_name'] = interactions_df['timestamp'].dt.day_name()
        
        return interactions_df['day_name'].mode()[0] if len(interactions_df) > 0 else "No data"
    
    def _get_top_genre(self, feedback_df: pd.DataFrame) -> str:
        genre_data = self._extract_genre_data(feedback_df)
        
        if not genre_data:
            return "No data"
        
        return max(genre_data, key=genre_data.get)

def show_analytics_page(user: Dict, db_manager):
    analytics_page = AnalyticsPage(db_manager)
    analytics_page.show_analytics_page(user, db_manager)