import json
import os
import requests
from datetime import datetime
from youtubesearchpython import VideosSearch
from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup

def fetch_full_description(video_url):
    response = requests.get(video_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    description = soup.find('meta', {'name': 'description'})
    return description['content'] if description else ''

def split_transcript(transcript, video_url, video_title, interval=45):
    split_transcripts = []
    current_content = []
    current_start = transcript[0]['start']
    current_end = current_start + interval

    for entry in transcript:
        start = entry['start']
        duration = entry.get('duration', 0)
        end = start + duration
        text = entry['text']

        if start < current_end:
            current_content.append(text)
        else:
            timestamp_url = f"{video_url}&start={int(current_start)}&end={int(current_end)}"
            split_transcripts.append({
                "start": current_start,
                "end": current_end,
                "content": ' '.join(current_content),
                "url": timestamp_url,
                "title": video_title
            })
            current_start = start
            current_end = current_start + interval
            current_content = [text]

    if current_content:
        timestamp_url = f"{video_url}&start={int(current_start)}&end={int(current_end)}"
        split_transcripts.append({
            "start": current_start,
            "end": current_end,
            "content": ' '.join(current_content),
            "url": timestamp_url,
            "title": video_title
        })

    return split_transcripts

def fetch_youtube_videos(channel_name, num_videos, st):
    unique_id = f"{channel_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    folder_path = os.path.join('transcripts', unique_id)
    os.makedirs(folder_path, exist_ok=True)

    videos_search = VideosSearch(channel_name, limit=50)
    videos = []
    total_transcript_length = 0
    total_videos = 0
    fetched_videos = 0

    while fetched_videos < num_videos:
        results = videos_search.result()['result']
        for i, video in enumerate(results):
            if fetched_videos >= num_videos:
                break
            video_url = video['link']
            video_title = video['title']
            video_descr = fetch_full_description(video_url)
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video['id'])
                split_transcripts = split_transcript(transcript, video_url, video_title)
                transcript_length = sum(len(t['content']) for t in split_transcripts)
                total_transcript_length += transcript_length
                total_videos += 1
                fetched_videos += 1

                videos.append({
                    'url': video_url,
                    'title': video_title,
                    'descr': video_descr,
                    'duration': video['duration'],
                    'lengthOfTranscript': transcript_length
                })

                transcript_filename = os.path.join(folder_path, f"transcript_{video['id']}.json")
                with open(transcript_filename, 'w') as transcript_file:
                    json.dump(split_transcripts, transcript_file, indent=4)
                
                st.write(f"Fetched transcript for video titled: {video_title}")
            except Exception as e:
                print(f"Failed to fetch transcript for video titled: {video_title}. Error: {str(e)}")
        if fetched_videos < num_videos and 'next' in videos_search.result():
            videos_search.next()
        else:
            break

    return folder_path, videos