import streamlit as st

def apply_custom_css():
    st.markdown("""
    <style>
        /* Main app styling */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        /* Header styling */
        .main-header {
            background: rgba(255, 255, 255, 0.1);
            padding: 1.5rem;
            border-radius: 15px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        
        /* Card styling */
        .track-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            transition: transform 0.3s ease;
        }
        
        .track-card:hover {
            transform: translateY(-5px);
        }
        
        /* Tag styling */
        .mood-indicator {
            background: linear-gradient(45deg, #ff6b6b, #feca57);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            display: inline-block;
            margin: 0.2rem;
            font-weight: bold;
            box-shadow: 0 4px 15px 0 rgba(255, 107, 107, 0.3);
        }
        
        .rl-indicator {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 0.3rem 0.8rem;
            border-radius: 15px;
            display: inline-block;
            margin: 0.2rem;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        /* Metric cards */
        .metric-card {
            background: rgba(255, 255, 255, 0.15);
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            margin: 0.5rem 0;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        /* Status boxes */
        .success-box {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.5);
            padding: 1rem;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        
        .info-box {
            background: rgba(33, 150, 243, 0.2);
            border: 1px solid rgba(33, 150, 243, 0.5);
            padding: 1rem;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        
        .warning-box {
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.5);
            padding: 1rem;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        
        /* Audio player styling */
        .audio-player {
            width: 100%;
            margin: 0.5rem 0;
            border-radius: 10px;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
        }
        
        /* Button styling */
        .stButton > button {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.5rem 1rem;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        
        /* Input styling */
        .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            color: white;
        }
        
        .stTextArea > div > div > textarea {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            color: white;
        }
        
        /* Hide Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(45deg, #667eea, #764ba2);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(45deg, #5a67d8, #6b46c1);
        }
    </style>
    """, unsafe_allow_html=True)

def create_metric_card(title: str, value: str, delta: str = None, color: str = "blue") -> str:
    """Create a styled metric card"""
    
    delta_html = ""
    if delta:
        delta_color = "green" if delta.startswith("+") else "red" if delta.startswith("-") else "gray"
        delta_html = f'<div style="color: {delta_color}; font-size: 0.8rem;">{delta}</div>'
    
    return f"""
    <div class="metric-card" style="border-left: 4px solid {color};">
        <div style="font-size: 1.5rem; font-weight: bold; color: white;">{value}</div>
        <div style="color: rgba(255,255,255,0.8); font-size: 0.9rem;">{title}</div>
        {delta_html}
    </div>
    """