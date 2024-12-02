import streamlit as st
import logging
import json
from typing import List, Dict
from pydantic import BaseModel
from openai import OpenAI
import os 
from dotenv import load_dotenv
import openai
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
flux = os.getenv("FLUX")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Set up logging
logging.basicConfig(level=logging.INFO)

class StorySegment(BaseModel):
    scene: str
    image: str

class StoryStructure(BaseModel):
    segments: List[StorySegment]

def generate_story(plot: str) -> Dict[str, str]:
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": """Create a short story (6-7 scenes) based on the given plot. For each scene, provide a description and an image prompt in comic format. Example:
                    plot: a space dog 
                    story : "scene: the super smart space dog is on a mission to conquer mars for humans
                    image: a corgi in a space suit looking serious in a rocket with mars in its eyes american comic style 1950s colorful
                    scene: the space dog finally reaches his destination and with great excitement steps out of his spaceship
                    image: the space dog in a desert with a thirst for conquering mars american comic style 1950s colorful"
                    Only reply in structured format.
                    if you have any characters describe them in a good manner such that when given to image generator it looks similar also if the user gives any famous character names keep the names consistent so the comic can look bit more consistent"""
                },
                {"role": "user", "content": plot}
            ],
            tools=[openai.pydantic_function_tool(StoryStructure)],
        )
        response = completion.choices[0].message
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            if tool_call.function.name == 'StoryStructure':
                story_data = json.loads(tool_call.function.arguments)["segments"]
                output_data = {}
                for i, segment in enumerate(story_data, 1):
                    output_data[f"scene_{i}"] = segment['scene']
                    output_data[f"image_{i}"] = segment['image']
                with open('media/output.json', 'w') as json_file:
                    json.dump(output_data, json_file, indent=4)
                return output_data
            else:
                logging.warning(f"Unexpected function call: {tool_call.function.name}")
                return {}
        else:
            logging.warning("No story data was extracted from the plot")
            return {}
    except Exception as e:
        st.error(f"Error during story generation: {str(e)}")
        return {}

def generate_image(prompt: str, scene_number: int) -> str:
    url = "https://api.segmind.com/v1/flux-schnell"
    data = {
        "prompt": prompt,
        "steps": 4,
        "seed": 123456789,
        "sampler_name": "euler",
        "scheduler": "normal",
        "samples": 1,
        "width": 1024,
        "height": 1024,
        "denoise": 1
    }

    try:
        response = requests.post(url, json=data, headers={'x-api-key': flux})
        if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
            img_path = os.path.join('media', f"image_{scene_number}.png")
            with open(img_path, 'wb') as img_file:
                img_file.write(response.content)
            return img_path
        else:
            st.error(f"Error generating image: {response.status_code}")
            return ""
    except requests.exceptions.RequestException as e:
        st.error(f"Error in generate_image: {str(e)}")
        return ""

def generate_narration(text: str, scene_number: int, audio_id: str = "lxF2pkpZKoiYamIvyhZ3") -> str:
    try:
        st.write(f"Generating audio for scene {scene_number}...")
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
        
        audio_path = os.path.join('media', f"narration_scene_{scene_number}.mp3")
        with open(audio_path, 'wb') as f:
            f.write(audio_data)
        
        return audio_path
    except Exception as e:
        st.error(f"Error in generate_narration: {str(e)}")
        return ""

async def generate_media_parallel(story_data: Dict[str, str]):
    try:
        os.makedirs('media', exist_ok=True)
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            loop = asyncio.get_event_loop()
            tasks = []
            
            scene_count = len([key for key in story_data.keys() if key.startswith('scene_')])
            
            for i in range(1, scene_count + 1):
                image_prompt = story_data.get(f"image_{i}")
                if image_prompt:
                    tasks.append(loop.run_in_executor(executor, generate_image, image_prompt, i))
            
            image_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(image_results, 1):
                if isinstance(result, Exception):
                    st.error(f"Error generating image for scene {i}: {str(result)}")
                elif result:
                    story_data[f"image_path_{i}"] = result
            
            tasks = []
            for i in range(1, scene_count + 1):
                narration_text = story_data.get(f"scene_{i}")
                if narration_text:
                    tasks.append(loop.run_in_executor(executor, generate_narration, narration_text, i))
                
                if len(tasks) == 2 or i == scene_count:
                    narration_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for j, result in enumerate(narration_results):
                        scene_num = i - len(narration_results) + j + 1
                        if isinstance(result, Exception):
                            st.error(f"Error generating narration for scene {scene_num}: {str(result)}")
                        elif result:
                            story_data[f"narration_path_{scene_num}"] = result
                    
                    tasks = []
                    await asyncio.sleep(1)
        
        with open('media/output.json', 'w') as json_file:
            json.dump(story_data, json_file, indent=4)
        
    except Exception as e:
        st.error(f"Error in generate_media_parallel: {str(e)}")

def main():
    st.title("Interactive Story Generator")

    plot = st.text_input("Enter a plot for your story:")

    if st.button("Generate Story"):
        with st.spinner("Generating story..."):
            story_data = generate_story(plot)

        with st.spinner("Creating images and narrations..."):
            asyncio.run(generate_media_parallel(story_data))

        st.success("Story, images, and narrations generated successfully!")

        scene_count = len([key for key in story_data.keys() if key.startswith('scene_')])
        for i in range(1, scene_count + 1, 2):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(f"Scene {i}")
                image_path = story_data.get(f"image_path_{i}")
                if image_path:
                    st.image(image_path)
                st.write(story_data.get(f"scene_{i}", "Scene text not available"))
                narration_path = story_data.get(f"narration_path_{i}")
                if narration_path:
                    st.audio(narration_path)
            
            if i+1 <= scene_count:
                with col2:
                    st.subheader(f"Scene {i+1}")
                    image_path = story_data.get(f"image_path_{i+1}")
                    if image_path:
                        st.image(image_path)
                    st.write(story_data.get(f"scene_{i+1}", "Scene text not available"))
                    narration_path = story_data.get(f"narration_path_{i+1}")
                    if narration_path:
                        st.audio(narration_path)

if __name__ == "__main__":
    main()