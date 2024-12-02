import streamlit as st
import replicate
import os
import json
import requests
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

replicate.api_token = os.getenv("REPLICATE_API_TOKEN")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def upload_file(file_path):
    """Upload a file to a temporary file hosting service and return the URL."""
    with open(file_path, 'rb') as file:
        response = requests.post('https://transfer.sh/', files={'file': file})
    if response.status_code == 200:
        return response.text.strip()
    else:
        raise Exception(f"Failed to upload {file_path}. Status code: {response.status_code}")

def generate_audio(audio_id, text):
    st.write("Generating audio...")
    client = ElevenLabs(
        api_key=ELEVENLABS_API_KEY,
    )
    audio_generator = client.text_to_speech.convert(
        voice_id=audio_id,
        optimize_streaming_latency="1",
        output_format="mp3_22050_32",
        text=text,
        voice_settings=VoiceSettings(
            stability=0.1,
            similarity_boost=0.3,
            style=0.2,
        ),
    )
    
    audio_data = b''.join(chunk for chunk in audio_generator)
    
    # Save the audio in the same directory as the Streamlit app
    with open('output.mp3', 'wb') as f:
        f.write(audio_data)
    
    st.success("Audio generated and saved as output.mp3")

def generate_video():
    st.write("Generating video...")
    output = replicate.run(
    "skytells-research/wav2lip:22b1ecf6252b8adcaeadde30bb672b199c125b7d3c98607db70b66eea21d75ae",
    input={
        "fps": 25,
        "face": "media/test.mp4",
        "pads": "0 10 0 0",
        "audio": "./media/test.mp3",
        "smooth": True,
        "out_height": 480
    }
    )
    
    output_json = json.loads(output)
    output_url = output_json['output']
    
    response = requests.get(output_url)
    
    # Save the video in the same directory as the Streamlit app
    with open('output.mp4', 'wb') as f:
        f.write(response.content)
    
    st.success("Video generated and saved as output.mp4")

def main():
    st.title("Argil AI Video Generator")

    text = st.text_area("Enter the text for audio generation:", "This is a demo of Argil AI, the app that rocks!")
    audio_id = st.text_input("Enter the audio ID:", "Hvj7HNqsooYQqK8egqvJ")

    if st.button("Generate Audio"):
        generate_audio(audio_id, text)

    if st.button("Generate Video"):
        generate_video()

    if st.button("Upload Video"):
        uploaded_url = upload_file("output.mp4")
        st.success(f"Video uploaded. URL: {uploaded_url}")

if __name__ == "__main__":
    main()