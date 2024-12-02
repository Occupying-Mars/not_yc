import streamlit as st
import os
import json
from qdrant_vector_store import QdrantVectorStore
from youtube_fetcher import fetch_youtube_videos
import datetime

vector_db = QdrantVectorStore()

st.title("Overlap")

st.write("""
This app allows you to fetch transcripts from a YouTube channel and upsert them into a Qdrant Vector Store for searching. 
1. Enter the YouTube channel name and the number of videos to fetch.
2. Click 'Fetch Transcripts' to fetch the transcripts.
3. Click 'Upsert into Vector DB' to upsert the fetched transcripts into the vector database.
4. Use the search functionality to search podcast clips through the upserted transcripts.
""")

channel_name = st.text_input("Enter YouTube Channel Name")

num_videos = st.number_input("Enter number of videos to fetch", min_value=1, max_value=50, value=10)

if st.button("Fetch Transcripts"):
    if channel_name:
        with st.spinner('Fetching videos and transcripts...'):
            folder_path, result = fetch_youtube_videos(channel_name, num_videos, st)
            st.write("Fetched videos and transcripts.")
            st.session_state['folder_path'] = folder_path
            st.session_state['transcripts_fetched'] = True
    else:
        st.write("Please enter a YouTube channel name.")

if 'transcripts_fetched' in st.session_state and st.session_state['transcripts_fetched']:
    if st.button("Upsert into Vector DB"):
        folder_path = st.session_state['folder_path']
        with st.spinner('Upserting transcripts into vector database...'):
            progress_bar = st.progress(0)
            total_files = len(os.listdir(folder_path))
            for i, filename in enumerate(os.listdir(folder_path)):
                if "transcript" in filename and filename.endswith(".json"):
                    with open(os.path.join(folder_path, filename), 'r') as file:
                        transcript_data = json.load(file)
                        vector_db.upsert_data(transcript_data, filename)
                        st.write(f"Data of video: {filename} uploaded successfully")
                        progress_bar.progress((i + 1) / total_files)
            st.write("Transcripts upserted into Qdrant Vector Store.")
            st.session_state['upserted'] = True

if 'upserted' in st.session_state and st.session_state['upserted']:
    search_query = st.text_input("Enter search query")

    if st.button("Search"):
        if search_query:
            results = vector_db.search(search_query)
            st.write('<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px;">', unsafe_allow_html=True)
            for result in results:
                start_time = str(datetime.timedelta(seconds=result['start'])).split('.')[0]
                end_time = str(datetime.timedelta(seconds=result['end'])).split('.')[0]
                st.write(f'''
                    <div style="border: 1px solid #c; padding: 10px; border-radius: 5px; margin: 10px">
                        <h3>Clip - Start: {start_time} End: {end_time} of Video {result['title']}</h3>
                        <p style="max-height: 3em; overflow: hidden; text-overflow: ellipsis;" onclick="this.style.maxHeight = this.style.maxHeight === 'none' ? '3em' : 'none'; this.style.cursor = 'pointer';">{result['content']}</p>
                        <a href="{result['url']}" target="_blank">Watch on YouTube</a>
                    </div>
                ''', unsafe_allow_html=True)
            st.write('</div>', unsafe_allow_html=True)
        else:
            st.write("Please enter a search query.")