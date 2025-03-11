# narrate.py

import os
import requests
import argparse
from dotenv import load_dotenv

def narrate_text(input_file, output_file, voice_id=None, stability=0.5, similarity_boost=0.75, style=0.1, speed=1.0):
    """
    Convert text to speech using ElevenLabs API.
    
    Args:
        input_file (str): Path to text file to narrate
        output_file (str): Path to save output MP3
        voice_id (str): Voice ID to use (default: Bill's voice)
        stability (float): Voice stability (0.0-1.0)
        similarity_boost (float): Voice similarity boost (0.0-1.0)
        style (float): Style exaggeration (0.0-1.0)
        speed (float): Speech speed (0.5-2.0)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Load environment variables
    load_dotenv()
    
    # Set up API key
    API_KEY = os.environ.get("ELEVENLABS_API_KEY")
    if not API_KEY:
        print("Error: ELEVENLABS_API_KEY not found in environment variables or .env file")
        return False
    
    # Use default voice if none provided (Bill's voice)
    if not voice_id:
        voice_id = "pqHfZKP75CvOlQylNhV4"  # Default to Bill's voice
    
    # Read the text from the input file
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            text_content = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}")
        return False
    
    # Send request to ElevenLabs API
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": API_KEY
    }
    
    payload = {
        "text": text_content,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "speed": speed
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            # Save the audio to the output file
            with open(output_file, "wb") as out:
                out.write(response.content)
            print(f"Narration saved to {output_file}")
            return True
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"Error making API request: {e}")
        return False

def main():
    """Handle command line arguments when run directly."""
    parser = argparse.ArgumentParser(description="Generate narration using ElevenLabs API.")
    parser.add_argument("--input", default="script.txt", help="Input text file path")
    parser.add_argument("--output", default="output.mp3", help="Output MP3 file path")
    parser.add_argument("--voice", default="pqHfZKP75CvOlQylNhV4", help="Voice ID to use")
    parser.add_argument("--stability", type=float, default=0.5, help="Voice stability (0.0-1.0)")
    parser.add_argument("--similarity", type=float, default=0.75, help="Voice similarity boost (0.0-1.0)")
    parser.add_argument("--style", type=float, default=0.1, help="Style exaggeration (0.0-1.0)")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed (0.5-2.0)")
    
    args = parser.parse_args()
    
    success = narrate_text(
        args.input, 
        args.output, 
        args.voice, 
        args.stability, 
        args.similarity, 
        args.style, 
        args.speed
    )
    
    if not success:
        print("Narration failed.")
        exit(1)

if __name__ == "__main__":
    main()