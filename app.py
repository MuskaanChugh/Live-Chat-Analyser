import streamlit as st
import anthropic
from dotenv import load_dotenv
import os
import pandas as pd
import time
import re
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import json
import requests
from urllib.parse import parse_qs, urlparse
import html

# Load environment variables
load_dotenv()

# Initialize Claude client
claude_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

class YouTubeChatAnalyzer:
    def __init__(self):
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        
    def extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/live\/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_live_chat_id(self, video_id):
        """Get live chat ID using YouTube API"""
        if not self.youtube_api_key:
            return None
            
        url = f"https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'liveStreamingDetails',
            'id': video_id,
            'key': self.youtube_api_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'items' in data and len(data['items']) > 0:
                live_details = data['items'][0].get('liveStreamingDetails', {})
                return live_details.get('activeLiveChatId')
        except Exception as e:
            st.error(f"Error getting live chat ID: {e}")
        
        return None
    
    def collect_chat_with_api(self, video_id, max_messages=100):
        """Collect chat using YouTube Data API"""
        if not self.youtube_api_key:
            st.error("YouTube API key required for this method. Please add YOUTUBE_API_KEY to your .env file")
            return []
        
        chat_id = self.get_live_chat_id(video_id)
        if not chat_id:
            st.error("Could not get live chat ID. Stream may not be live or chat may be disabled.")
            return []
        
        messages = []
        next_page_token = None
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            while len(messages) < max_messages:
                url = f"https://www.googleapis.com/youtube/v3/liveChat/messages"
                params = {
                    'liveChatId': chat_id,
                    'part': 'snippet,authorDetails',
                    'key': self.youtube_api_key,
                    'maxResults': min(200, max_messages - len(messages))
                }
                
                if next_page_token:
                    params['pageToken'] = next_page_token
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'items' not in data:
                    break
                
                for item in data['items']:
                    snippet = item['snippet']
                    author = item['authorDetails']
                    
                    message_data = {
                        'author': author.get('displayName', 'Unknown'),
                        'message': snippet.get('displayMessage', ''),
                        'timestamp': snippet.get('publishedAt', ''),
                        'author_channel_id': author.get('channelId', ''),
                        'is_moderator': author.get('isChatModerator', False),
                        'is_owner': author.get('isChatOwner', False),
                        'is_verified': author.get('isVerified', False),
                        'message_type': snippet.get('type', 'textMessageEvent')
                    }
                    messages.append(message_data)
                
                progress = len(messages) / max_messages
                progress_bar.progress(min(progress, 1.0))
                status_text.text(f"Collecting messages... {len(messages)} messages collected")
                
                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break
                
                # Respect rate limits
                time.sleep(1)
        
        except Exception as e:
            st.error(f"Error collecting chat: {e}")
        
        status_text.text(f"Collection complete! Collected {len(messages)} messages")
        return messages
    
    def simulate_chat_data(self, num_messages=50):
        """Generate simulated chat data for testing purposes"""
        import random
        
        sample_users = [
            "StreamFan123", "ChatMaster", "LiveViewer", "YouTubeUser", "VideoLover",
            "ChatBot2024", "StreamWatcher", "CommentKing", "ViewerPro", "ChatExpert"
        ]
        
        sample_messages = [
            "Great stream!", "Love this content!", "When will the next stream be?",
            "Amazing work!", "Can you explain that again?", "First time watching!",
            "This is so helpful", "What software do you use?", "How long have you been streaming?",
            "Can you show that part again?", "Love the energy!", "New subscriber here!",
            "What's your favorite tool?", "This is exactly what I needed",
            "When did you start?", "Do you have a tutorial for this?",
            "Can you go slower?", "This is confusing", "Great explanation!",
            "What's next?", "How do I get started?", "Thanks for sharing!",
            "This is incredible", "Mind blown!", "So cool!", "Awesome content",
            "Keep it up!", "You're the best!", "Learning so much", "Great teacher"
        ]
        
        messages = []
        base_time = datetime.now()
        
        for i in range(num_messages):
            message_data = {
                'author': random.choice(sample_users),
                'message': random.choice(sample_messages),
                'timestamp': (base_time - pd.Timedelta(minutes=random.randint(1, 30))).isoformat(),
                'author_channel_id': f"UC{random.randint(100000, 999999)}",
                'is_moderator': random.choice([True, False]) if random.random() < 0.1 else False,
                'is_owner': False,
                'is_verified': random.choice([True, False]) if random.random() < 0.05 else False,
                'message_type': 'textMessageEvent'
            }
            messages.append(message_data)
        
        return messages
    
    def collect_chat_manual_input(self):
        """Allow manual input of chat messages for testing"""
        st.subheader("Manual Chat Input")
        st.info("Since live chat collection isn't working, you can manually input some sample messages to test the analysis.")
        
        messages = []
        
        with st.form("manual_chat_form"):
            st.write("Enter chat messages (one per line, format: Username: Message)")
            chat_input = st.text_area(
                "Chat Messages",
                height=200,
                placeholder="StreamFan123: This is amazing!\nViewerPro: How do you do that?\nChatMaster: Great explanation!"
            )
            
            submitted = st.form_submit_button("Process Messages")
            
            if submitted and chat_input:
                lines = chat_input.strip().split('\n')
                
                for i, line in enumerate(lines):
                    if ':' in line:
                        parts = line.split(':', 1)
                        author = parts[0].strip()
                        message = parts[1].strip()
                    else:
                        author = f"User{i+1}"
                        message = line.strip()
                    
                    if message:
                        message_data = {
                            'author': author,
                            'message': message,
                            'timestamp': (datetime.now() - pd.Timedelta(minutes=len(lines)-i)).isoformat(),
                            'author_channel_id': f"UC{hash(author) % 1000000}",
                            'is_moderator': False,
                            'is_owner': False,
                            'is_verified': False,
                            'message_type': 'textMessageEvent'
                        }
                        messages.append(message_data)
        
        return messages
    
    def analyze_with_claude(self, messages, analysis_type="comprehensive"):
        """Analyze chat messages using Claude API"""
        if not messages:
            return "No messages to analyze"
        
        # Prepare message text for analysis
        chat_text = "\n".join([f"{msg['author']}: {msg['message']}" for msg in messages[-300:]])  # Last 300 messages
        
        prompts = {
            "comprehensive": f"""
            Please analyze this YouTube live chat data and provide comprehensive insights:

            **Analysis Required:**
            1. **Key Themes & Topics**: What are the main subjects being discussed?
            2. **Most Frequent Questions**: What questions do viewers ask most often?
            3. **Sentiment & Mood**: What's the overall emotional tone and audience engagement level?
            4. **Notable Moments**: Any significant reactions, trending topics, or viral moments?
            5. **Community Engagement**: How is the audience interacting? Are there power users, moderators active?
            6. **Content Feedback**: What do viewers think about the content being streamed?

            **Chat Messages:**
            {chat_text}

            Please provide detailed insights with specific examples from the chat where relevant.
            """,
            
            "questions": f"""
            Please extract and analyze all the questions asked by viewers in this YouTube live chat.

            **Tasks:**
            1. **Identify Questions**: Find all direct and indirect questions
            2. **Categorize by Topic**: Group similar questions together
            3. **Frequency Analysis**: Which questions or question types appear most often?
            4. **Answer Status**: Which questions seem answered vs unanswered?
            5. **Question Quality**: Are questions technical, casual, or seeking clarification?

            **Chat Messages:**
            {chat_text}

            Format your response with clear categories and specific examples.
            """,
            
            "sentiment": f"""
            Please analyze the emotional tone and sentiment of this YouTube live chat.

            **Analysis Focus:**
            1. **Overall Sentiment**: Positive, negative, or neutral tone?
            2. **Emotional Patterns**: Excitement, frustration, confusion, appreciation?
            3. **Engagement Level**: How actively engaged is the audience?
            4. **Community Vibe**: Supportive, critical, or mixed?
            5. **Mood Changes**: Any shifts in sentiment during the chat?
            6. **Standout Reactions**: Notable emotional responses or reactions?

            **Chat Messages:**
            {chat_text}

            Provide specific examples and explain the reasoning behind your sentiment analysis.
            """,
            
            "themes": f"""
            Please identify and analyze the main themes and topics discussed in this YouTube live chat.

            **Analysis Goals:**
            1. **Primary Themes**: What are the 3-5 most discussed topics?
            2. **Trending Topics**: What subjects gained momentum during the chat?
            3. **Recurring Discussions**: What topics keep coming up repeatedly?
            4. **Topic Evolution**: How do conversations shift and develop?
            5. **Audience Interests**: What does the chat reveal about viewer preferences?
            6. **Content Alignment**: How well do chat topics align with the stream content?

            **Chat Messages:**
            {chat_text}

            Organize your response by theme and provide supporting evidence from the chat.
            """
        }
        
        try:
            response = claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                temperature=0.3,
                system="You are an expert social media analyst specializing in live chat analysis. You provide detailed, insightful, and actionable analysis of online community interactions. Your analysis is always backed by specific examples and evidence from the data.",
                messages=[
                    {
                        "role": "user",
                        "content": prompts[analysis_type]
                    }
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"Error analyzing chat with Claude: {str(e)}"
    
    def generate_chat_statistics(self, messages):
        """Generate basic statistics about the chat"""
        if not messages:
            return {}
        
        df = pd.DataFrame(messages)
        
        stats = {
            'total_messages': len(messages),
            'unique_users': df['author'].nunique(),
            'messages_per_user': len(messages) / df['author'].nunique() if df['author'].nunique() > 0 else 0,
            'moderator_messages': df['is_moderator'].sum(),
            'owner_messages': df['is_owner'].sum(),
            'verified_messages': df['is_verified'].sum(),
            'top_chatters': df['author'].value_counts().head(10).to_dict(),
            'message_length_avg': df['message'].str.len().mean() if len(df) > 0 else 0,
        }
        
        return stats

def main():
    st.set_page_config(
        page_title="YouTube Live Chat Analyzer",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 YouTube Live Chat Analyzer (Powered by Claude)")
    st.markdown("Analyze YouTube live chat messages using Claude AI to extract key insights, questions, and themes!")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Check API keys
        if not os.getenv('ANTHROPIC_API_KEY'):
            st.error("⚠️ Claude API key not found! Please set ANTHROPIC_API_KEY in your .env file.")
            st.stop()
        else:
            st.success("✅ Claude API key loaded")
        
        if not os.getenv('YOUTUBE_API_KEY'):
            st.warning("⚠️ YouTube API key not found. Some features will be limited.")
        else:
            st.success("✅ YouTube API key loaded")
        
        collection_method = st.selectbox(
            "Collection Method",
            ["YouTube Data API", "Simulated Data (Demo)", "Manual Input"],
            help="Choose how to collect chat data"
        )
        
        if collection_method == "YouTube Data API":
            max_messages = st.slider("Max Messages to Collect", 50, 500, 100)
        elif collection_method == "Simulated Data (Demo)":
            num_messages = st.slider("Number of Sample Messages", 20, 200, 50)
            
        analysis_type = st.selectbox(
            "Analysis Type",
            ["comprehensive", "questions", "sentiment", "themes"],
            help="Choose what type of analysis to perform"
        )
    
    # Main interface
    analyzer = YouTubeChatAnalyzer()
    
    if collection_method == "Manual Input":
        # Manual input mode
        messages = analyzer.collect_chat_manual_input()
        
        if messages:
            st.success(f"✅ {len(messages)} messages processed!")
            analyze_messages(analyzer, messages, analysis_type)
    
    elif collection_method == "Simulated Data (Demo)":
        # Demo mode with simulated data
        st.info("Demo Mode: Using simulated chat data for testing")
        
        if st.button("🚀 Generate Demo Analysis", type="primary"):
            with st.spinner("Generating simulated chat data..."):
                messages = analyzer.simulate_chat_data(num_messages)
            
            if messages:
                st.success(f"✅ Generated {len(messages)} simulated messages!")
                analyze_messages(analyzer, messages, analysis_type)
    
    else:
        # YouTube API mode
        youtube_url = st.text_input(
            "Enter YouTube Live Stream URL:",
            placeholder="https://www.youtube.com/watch?v=VIDEO_ID or https://youtu.be/VIDEO_ID",
            help="Paste the URL of a YouTube live stream"
        )
        
        if youtube_url:
            video_id = analyzer.extract_video_id(youtube_url)
            
            if video_id:
                st.success(f"✅ Video ID extracted: {video_id}")
                
                if st.button("🚀 Start Analysis", type="primary"):
                    st.header("📊 Analysis Results")
                    
                    with st.spinner("Collecting chat messages using YouTube API..."):
                        messages = analyzer.collect_chat_with_api(video_id, max_messages)
                    
                    if messages:
                        analyze_messages(analyzer, messages, analysis_type)
                    else:
                        st.error("""
                        No messages collected. This could be because:
                        - The stream is not currently live
                        - Chat is disabled for this stream
                        - The video is private/unlisted
                        - YouTube API quota exceeded
                        
                        Try using "Simulated Data (Demo)" mode to test the analysis features.
                        """)
            
            else:
                st.error("❌ Invalid YouTube URL. Please check the format.")
    
    # Instructions
    with st.expander("📋 Instructions & Troubleshooting"):
        st.markdown("""
        ## Collection Methods:
        
        **1. YouTube Data API (Recommended)**
        - Requires YouTube API key in .env file
        - Works with live streams that have chat enabled
        - Most reliable method
        
        **2. Simulated Data (Demo)**
        - No API keys required
        - Uses sample chat data for testing
        - Perfect for trying out the analysis features
        
        **3. Manual Input**
        - Enter your own chat messages
        - Good for analyzing exported chat data
        - Format: "Username: Message" (one per line)
        
        ## Setup:
        1. Get Anthropic API key from https://console.anthropic.com/
        2. Add to .env file: `ANTHROPIC_API_KEY=your_key_here`
        3. Get YouTube Data API key from Google Cloud Console
        4. Add to .env file: `YOUTUBE_API_KEY=your_key_here`
        
        ## Notes:
        - Only works with currently live streams
        - Chat must be enabled on the stream
        - API quotas may limit collection
        """)

def analyze_messages(analyzer, messages, analysis_type):
    """Helper function to analyze and display results"""
    # Display basic statistics
    stats = analyzer.generate_chat_statistics(messages)
    
    st.subheader("📈 Chat Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Messages", stats['total_messages'])
    with col2:
        st.metric("Unique Users", stats['unique_users'])
    with col3:
        st.metric("Avg Messages/User", f"{stats['messages_per_user']:.1f}")
    with col4:
        st.metric("Avg Message Length", f"{stats['message_length_avg']:.1f}")
    
    # Top chatters chart
    if stats['top_chatters']:
        st.subheader("🏆 Most Active Chatters")
        top_chatters_df = pd.DataFrame(
            list(stats['top_chatters'].items()),
            columns=['User', 'Messages']
        )
        fig = px.bar(top_chatters_df, x='User', y='Messages', 
                   title="Top 10 Most Active Users")
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
    
    # AI Analysis
    st.subheader("🤖 Claude AI Analysis")
    with st.spinner("Analyzing with Claude..."):
        analysis = analyzer.analyze_with_claude(messages, analysis_type)
    
    st.markdown(analysis)
    
    # Message timeline
    if len(messages) > 1:
        st.subheader("⏱️ Message Timeline")
        df = pd.DataFrame(messages)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['minute'] = df['timestamp'].dt.floor('T')
        timeline = df.groupby('minute').size().reset_index(name='message_count')
        
        if len(timeline) > 1:
            fig_timeline = px.line(timeline, x='minute', y='message_count',
                                 title='Messages per Minute')
            st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Raw data download
    st.subheader("📥 Download Data")
    df = pd.DataFrame(messages)
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Chat Data as CSV",
        data=csv,
        file_name=f"youtube_chat_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # Sample messages
    with st.expander("👀 View Sample Messages"):
        st.dataframe(df[['author', 'message', 'timestamp']].head(20))

if __name__ == "__main__":
    main()