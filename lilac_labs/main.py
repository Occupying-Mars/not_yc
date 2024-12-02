import streamlit as st
import logging
import json
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Dict, Union
from dotenv import load_dotenv
import openai
from openai import OpenAI
import os

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class OrderItem(BaseModel):
    order_item: str
    item_quantity: int
    special_instructions: str

class OrderStructure(BaseModel):
    items: List[OrderItem]

def transcribe_audio(audio_file) -> Dict[str, Dict[str, Union[str, float]]]:
    try:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
        )
        
        response_dict = response.to_dict()
        
        transcription_data = {}
        for idx, segment in enumerate(response_dict.get("segments", []), 1):
            segment_key = f"segment_{idx}"
            transcription_data[segment_key] = {
                "text": segment.get("text", ""),
                "start": segment.get("start", 0),
                "end": segment.get("end", 0)
            }
        
        # Save transcription to media folder
        os.makedirs("media", exist_ok=True)
        with open("media/transcription.json", "w") as f:
            json.dump(transcription_data, f, indent=2)
        
        return transcription_data
    except Exception as e:
        logging.error(f"Error during transcription: {str(e)}")
        raise

def summarize_order(transcript: str) -> List[Dict[str, Union[str, int]]]:
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": "Here is the transcription of a user's order. Just give the order item name and its quantity and a special request if any. you take from this reply only in structured format"
                },
                {"role": "user", "content": transcript}
            ],
            tools=[
                openai.pydantic_function_tool(OrderStructure),
            ],
        )

        response = completion.choices[0].message
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            if tool_call.function.name == 'OrderStructure':
                return json.loads(tool_call.function.arguments)["items"]
        return []
    except Exception as e:
        logging.error(f"Error during order summarization: {str(e)}")
        raise

def main():
    st.title("Food Order Transcription and Summary")

    # Audio recording
    audio_file = st.file_uploader("Upload an audio file of your order", type=["wav", "mp3", "m4a"])
    
    if audio_file:
        st.audio(audio_file)

        if st.button("Process Order"):
            try:
                with st.spinner("Transcribing and summarizing your order..."):
                    # Transcribe audio
                    transcription_data = transcribe_audio(audio_file)
                    transcript = " ".join([segment['text'] for segment in transcription_data.values()])
                    
                    st.subheader("Transcript:")
                    st.write(transcript)

                    # Summarize order
                    order_summary = summarize_order(transcript)

                    # Display order summary
                    st.subheader("Order Summary:")
                    for item in order_summary:
                        st.write(f"- {item['order_item']}: {item['item_quantity']}")
                        if item['special_instructions']:
                            st.write(f"  Special Instructions: {item['special_instructions']}")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                logging.error(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    main()