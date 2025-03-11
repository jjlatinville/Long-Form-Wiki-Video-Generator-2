#!/usr/bin/env python3
# video_creator.py

import os
import argparse
import json
import time
import subprocess
import requests
import re
from dotenv import load_dotenv
from wiki_grabber import extract_wiki_title, get_wiki_content_via_api, process_wiki_content
from wiki_grabber import get_commons_category_images, download_thumbnail_images
import openai

# Load environment variables from .env file
load_dotenv()

# Configure OpenAI API
openai.api_key = os.environ.get("OPENAI_API_KEY")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Create a video from Wikipedia content.")
    parser.add_argument("--title", required=True, help="Title of the video")
    parser.add_argument("--links", required=True, nargs='+', help="One or more Wikipedia URLs")
    parser.add_argument("--length", type=int, default=2000, 
                        help="Target character count for the script (default: 2000)")
    parser.add_argument("--output", default="output_video.mp4", help="Output video filename")
    parser.add_argument("--temp_dir", default="temp", help="Directory for temporary files")
    parser.add_argument("--no-title-cards", action="store_true", help="Disable intro and outro title cards")
    
    return parser.parse_args()

def setup_directories(temp_dir):
    """Create necessary directories if they don't exist."""
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(f"{temp_dir}/wiki_content", exist_ok=True)
    os.makedirs(f"{temp_dir}/images", exist_ok=True)
    os.makedirs(f"{temp_dir}/audio", exist_ok=True)
    os.makedirs(f"{temp_dir}/subtitles", exist_ok=True)

def fetch_wiki_content(links, temp_dir):
    """Fetch content from Wikipedia using wiki_grabber.py."""
    all_content = []
    all_images = []
    
    for i, link in enumerate(links):
        print(f"Processing Wikipedia link {i+1}/{len(links)}: {link}")
        page_title = extract_wiki_title(link)
        
        if not page_title:
            print(f"Could not extract page title from URL: {link}")
            continue
            
        print(f"Page title: {page_title}")
        
        # Get content using the API
        wiki_data = get_wiki_content_via_api(page_title)
        
        if wiki_data:
            text_content, html_content = process_wiki_content(wiki_data)
            
            # Save content to a file
            content_file = f"{temp_dir}/wiki_content/wiki_{i}.txt"
            with open(content_file, "w", encoding="utf-8") as f:
                f.write(text_content)
            
            all_content.append({
                "title": page_title,
                "content": text_content,
                "file": content_file
            })
            
            # Get images
            print(f"Fetching images for: {page_title}")
            images = get_commons_category_images(page_title, max_images=10)
            
            if images:
                image_dir = f"{temp_dir}/images/{i}_{page_title.replace(' ', '_')}"
                os.makedirs(image_dir, exist_ok=True)
                saved_images = download_thumbnail_images(images, folder=image_dir, min_width=1280)
                
                if saved_images:
                    all_images.extend(saved_images)
                    print(f"Downloaded {len(saved_images)} images for {page_title}")
            else:
                print(f"No images found for {page_title}")
        else:
            print(f"Failed to retrieve Wikipedia content for: {page_title}")
    
    return all_content, all_images

def generate_script(title, wiki_contents, target_length):
    """Generate a script using OpenAI based on the Wikipedia content."""
    combined_content = ""
    for item in wiki_contents:
        combined_content += f"=== {item['title']} ===\n"
        # Limit each wiki section to manage token usage
        combined_content += item['content'][:8000] + "\n\n"
    
    # Prepare the prompt for the AI
    system_prompt = (
        f"You are a skilled scriptwriter creating a video titled '{title}'. "
        f"Use the following Wikipedia content to create an engaging, educational script "
        f"of approximately {target_length} characters. "
        f"The script should flow naturally, be engaging, and include interesting facts and details. "
        f"Organize the content in a way that makes sense for the title. "
        f"Format the script with clear paragraph breaks to indicate natural image transitions. "
        f"Never mention that the information comes from Wikipedia."
    )
    
    # Get the script from OpenAI
    try:
        print("Generating script with AI...")
        response = openai.chat.completions.create(
            model="gpt-4-turbo",  # Use an appropriate model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_content}
            ],
            max_tokens=3000,
            temperature=0.7
        )
        
        script = response.choices[0].message.content.strip()
        print(f"Script generated ({len(script)} characters)")
        return script
    
    except Exception as e:
        print(f"Error generating script: {e}")
        # Fallback to a simple script
        return f"Welcome to {title}.\n\nLet's explore this fascinating topic together."

def split_script_into_paragraphs(script):
    """Split the script into logical paragraphs for better synchronization with images."""
    # First split by double newlines (common paragraph separator)
    paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]
    
    # If we don't have enough paragraphs, try to split by single newlines
    if len(paragraphs) < 5:
        paragraphs = [p.strip() for p in script.split('\n') if p.strip()]
    
    # If we still don't have enough or paragraphs are very long, split by sentences
    if len(paragraphs) < 5 or max(len(p) for p in paragraphs) > 500:
        sentence_endings = r'(?<=[.!?])\s+'
        new_paragraphs = []
        
        for p in paragraphs:
            sentences = re.split(sentence_endings, p)
            # Group sentences into reasonable paragraph lengths
            current_group = ""
            for sentence in sentences:
                if len(current_group) + len(sentence) < 300:
                    current_group += " " + sentence if current_group else sentence
                else:
                    if current_group:
                        new_paragraphs.append(current_group.strip())
                    current_group = sentence
            
            if current_group:  # Add the last group
                new_paragraphs.append(current_group.strip())
        
        paragraphs = new_paragraphs
    
    return paragraphs

def create_narration(script, temp_dir):
    """Create narration using narrate.py module."""
    from narrate_updated import narrate_text
    
    script_file = f"{temp_dir}/script.txt"
    narration_file = f"{temp_dir}/audio/narration.mp3"
    
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(script)
    
    print("Generating narration using ElevenLabs...")
    try:
        # Call our updated narration function directly
        success = narrate_text(
            input_file=script_file,
            output_file=narration_file,
            voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "pqHfZKP75CvOlQylNhV4"),  # Default to Bill's voice
            stability=0.5,
            similarity_boost=0.75,
            style=0.1,
            speed=1.0
        )
        
        if success:
            return narration_file
        else:
            print("Failed to generate narration.")
            return None
    except Exception as e:
        print(f"Error generating narration: {e}")
        return None

def generate_subtitles(narration_file, script, temp_dir):
    """Generate subtitles from the narration using speech-to-text or timing estimation."""
    # For simplicity, we'll create a basic subtitle file with estimated timing
    # In a more advanced version, you would use proper speech recognition or the ElevenLabs API
    
    # Estimate 15 characters per second (adjust based on your narrator's speed)
    chars_per_second = 15
    
    # Get audio duration
    try:
        ffprobe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", narration_file
        ]
        audio_duration = float(subprocess.check_output(ffprobe_cmd).decode('utf-8').strip())
        
        # Adjust chars_per_second based on actual audio length if needed
        total_chars = len(script)
        if audio_duration > 0 and total_chars > 0:
            chars_per_second = total_chars / audio_duration
            print(f"Adjusted timing: {chars_per_second:.2f} characters per second")
    except Exception as e:
        print(f"Warning: Could not get audio duration: {e}")
        # Continue with default estimate
    
    words = script.split()
    
    current_time = 0
    subtitle_content = ""
    line = ""
    line_chars = 0
    subtitle_count = 1
    
    for word in words:
        if line_chars + len(word) + 1 <= 60:  # Keep lines under 60 characters
            if line:
                line += " " + word
            else:
                line = word
            line_chars += len(word) + 1
        else:
            # Calculate timing for this line
            duration = line_chars / chars_per_second
            end_time = current_time + duration
            
            # Format in SRT format
            subtitle_content += f"{subtitle_count}\n"
            subtitle_content += f"{format_time(current_time)} --> {format_time(end_time)}\n"
            subtitle_content += f"{line}\n\n"
            
            subtitle_count += 1
            current_time = end_time
            line = word
            line_chars = len(word)
    
    # Add the last line
    if line:
        duration = line_chars / chars_per_second
        end_time = current_time + duration
        
        subtitle_content += f"{subtitle_count}\n"
        subtitle_content += f"{format_time(current_time)} --> {format_time(end_time)}\n"
        subtitle_content += f"{line}\n\n"
    
    subtitle_file = f"{temp_dir}/subtitles/subtitles.srt"
    with open(subtitle_file, "w", encoding="utf-8") as f:
        f.write(subtitle_content)
    
    return subtitle_file

def format_time(seconds):
    """Format time in SRT format: HH:MM:SS,mmm."""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds_int = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"

def create_video_with_segments(title, narration_file, subtitle_file, images, paragraphs, output_file, temp_dir):
    """Create a video with better segment/image synchronization based on script paragraphs."""
    if not images:
        print("No images available for the video.")
        return False
    
    try:
        # Determine audio duration
        ffprobe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", narration_file
        ]
        audio_duration = float(subprocess.check_output(ffprobe_cmd).decode('utf-8').strip())
        
        # Handle the case where we have more paragraphs than images
        if len(paragraphs) > len(images):
            # Group some paragraphs together
            ratio = len(paragraphs) / len(images)
            new_paragraphs = []
            current_group = ""
            
            for i, p in enumerate(paragraphs):
                current_group += p + " "
                if (i + 1) % ratio < 1 or i == len(paragraphs) - 1:
                    new_paragraphs.append(current_group.strip())
                    current_group = ""
            
            paragraphs = new_paragraphs
        
        # If we still have more paragraphs than images, we'll need to reuse some images
        while len(paragraphs) > len(images):
            images.append(images[len(images) % len(images)])
        
        # If we have more images than paragraphs, trim the image list
        if len(images) > len(paragraphs):
            images = images[:len(paragraphs)]
        
        # Calculate time per paragraph based on character count ratio
        total_chars = sum(len(p) for p in paragraphs)
        paragraph_durations = []
        
        for p in paragraphs:
            char_ratio = len(p) / total_chars
            duration = audio_duration * char_ratio
            paragraph_durations.append(duration)
        
        # Create a file with image transitions
        image_list_file = f"{temp_dir}/image_list.txt"
        with open(image_list_file, "w", encoding="utf-8") as f:
            for i, (image, duration) in enumerate(zip(images, paragraph_durations)):
                f.write(f"file '{image}'\n")
                f.write(f"duration {duration}\n")
            
            # Add the last image again to avoid a "last image duration" warning
            f.write(f"file '{images[-1]}'\n")
        
        # Create the video with images
        print("Creating video with images...")
        video_temp = f"{temp_dir}/temp_video.mp4"
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", image_list_file,
            "-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p", video_temp
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Add audio to the video
        print("Adding narration to video...")
        video_with_audio = f"{temp_dir}/video_with_audio.mp4"
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", video_temp, "-i", narration_file,
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-shortest", video_with_audio
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Add subtitles to the video
        print("Adding subtitles to video...")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", video_with_audio, "-vf",
            f"subtitles={subtitle_file}:force_style='FontSize=24,FontName=Arial,Alignment=2,BorderStyle=4,OutlineColour=&H40000000,BackColour=&H40000000'",
            "-c:a", "copy", output_file
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        print(f"Video created successfully: {output_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error creating video: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def create_video(title, narration_file, subtitle_file, images, output_file, temp_dir):
    """Create the final video with narration, subtitles, and images."""
    if not images:
        print("No images available for the video.")
        return False
    
    try:
        # First, determine audio duration
        ffprobe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", narration_file
        ]
        audio_duration = float(subprocess.check_output(ffprobe_cmd).decode('utf-8').strip())
        
        # Create a file with image transitions
        image_list_file = f"{temp_dir}/image_list.txt"
        with open(image_list_file, "w", encoding="utf-8") as f:
            images_count = len(images)
            duration_per_image = audio_duration / images_count
            
            for i, image in enumerate(images):
                f.write(f"file '{image}'\n")
                f.write(f"duration {duration_per_image}\n")
            
            # Add the last image again to avoid a "last image duration" warning
            f.write(f"file '{images[-1]}'\n")
        
        # Create the video with images
        print("Creating video with images...")
        video_temp = f"{temp_dir}/temp_video.mp4"
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", image_list_file,
            "-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p", video_temp
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Add audio to the video
        print("Adding narration to video...")
        video_with_audio = f"{temp_dir}/video_with_audio.mp4"
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", video_temp, "-i", narration_file,
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-shortest", video_with_audio
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Add subtitles to the video
        print("Adding subtitles to video...")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", video_with_audio, "-vf",
            f"subtitles={subtitle_file}:force_style='FontSize=24,Alignment=2'",
            "-c:a", "copy", output_file
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        print(f"Video created successfully: {output_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error creating video: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def main():
    """Main function to coordinate the video creation process."""
    args = parse_arguments()
    
    print(f"Creating video: {args.title}")
    print(f"Using {len(args.links)} Wikipedia links")
    print(f"Target script length: {args.length} characters")
    
    # Set up directories
    setup_directories(args.temp_dir)
    
    # Fetch Wikipedia content
    wiki_contents, images = fetch_wiki_content(args.links, args.temp_dir)
    
    if not wiki_contents:
        print("No Wikipedia content could be retrieved. Exiting.")
        return
    
    # Generate script
    script = generate_script(args.title, wiki_contents, args.length)
    script_file = f"{args.temp_dir}/script.txt"
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"Script saved to {script_file}")
    
    # Split script into paragraphs for better video timing
    paragraphs = split_script_into_paragraphs(script)
    print(f"Script split into {len(paragraphs)} paragraphs for timing")
    
    # Create narration
    narration_file = create_narration(script, args.temp_dir)
    if not narration_file:
        print("Failed to create narration. Exiting.")
        return
    
    # Generate subtitles
    subtitle_file = generate_subtitles(narration_file, script, args.temp_dir)
    
    # Create a base video without title cards
    base_output = f"{args.temp_dir}/base_video.mp4"
    
    # Create the video with paragraph-based timing
    success = create_video_with_segments(
        args.title, narration_file, subtitle_file, 
        images, paragraphs, base_output, args.temp_dir
    )
    
    if not success:
        print("Video creation failed. Trying simpler approach...")
        # Fallback to simpler video creation if the advanced method fails
        success = create_video(
            args.title, narration_file, subtitle_file, 
            images, base_output, args.temp_dir
        )
        
        if not success:
            print("Video creation failed with both methods.")
            return
    
    # Add title cards if not disabled
    if args.no_title_cards:
        print("Title cards disabled, using base video as final output.")
        import shutil
        shutil.copy(base_output, args.output)
        print(f"Video creation complete. Output file: {args.output}")
    else:
        from title_cards import add_title_cards_to_video
        try:
            print("Adding title cards to video...")
            final_video = add_title_cards_to_video(base_output, args.title, args.temp_dir, args.output)
            print(f"Final video with title cards created: {args.output}")
        except Exception as e:
            print(f"Error adding title cards: {e}")
            print("Using video without title cards as final output.")
            import shutil
            shutil.copy(base_output, args.output)
            print(f"Video creation complete. Output file: {args.output}")

if __name__ == "__main__":
    main()
