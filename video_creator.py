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
import openai
from pixabay_image_fetcher import get_relevant_images_for_script


def normalize_path_list(file_list):
    """
    Normalize all paths in a list to use forward slashes for FFmpeg compatibility.
    Also ensures absolute paths are properly formatted.
    """
    normalized = []
    for path in file_list:
        # Convert to absolute path
        path = os.path.abspath(path)
        
        # Convert Windows backslashes to forward slashes
        path = path.replace('\\', '/')
        
        # Remove any duplicate slashes
        path = re.sub(r'/+', '/', path)
        
        # Ensure no duplicate temp directories
        path = re.sub(r'(^|/)temp/temp/', r'\1temp/', path)
        
        normalized.append(path)
    
    return normalized

def normalize_path(path):
    """
    Normalize a path for cross-platform compatibility with FFmpeg.
    """
    # Get absolute path
    path = os.path.abspath(path)
    
    # Remove any duplicate directory references
    path = re.sub(r'(/|\\)temp\1temp\1', r'\1temp\1', path)
    
    # For Windows: handle path format
    if os.name == 'nt':
        # Ensure the path has a drive letter
        if not re.match(r'^[a-zA-Z]:', path):
            # Add current drive if needed
            drive = os.getcwd().split(':')[0]
            path = f"{drive}:{path[1:]}" if path.startswith('/') else f"{drive}:{path}"
        
        # Convert backslashes to forward slashes for FFmpeg
        path = path.replace('\\', '/')
    
    return path

def escape_path_for_ffmpeg(path):
    """
    Properly escape a file path for FFmpeg filter commands.
    """
    # Convert to absolute path and normalize slashes
    path = normalize_path(os.path.abspath(path))
    
    # For Windows: escape the colon in drive letter and use forward slashes
    if os.name == 'nt':
        # If path has a drive letter like C:, escape the colon
        if re.match(r'^[a-zA-Z]:', path):
            path = path.replace(':', '\\:')
    
    # Escape special characters
    path = path.replace("'", "'\\''")
    path = path.replace("\\", "/")
    
    return path

# Load environment variables from .env file
load_dotenv()

# Configure OpenAI API
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Add the --test-narration parameter to parse_arguments function
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
    parser.add_argument("--test-narration", action="store_true", help="Use test narration audio from test_audio folder")
    parser.add_argument("--test-audio-dir", default="test_audio", help="Directory with test audio files")
    # Add the new argument for Pixabay API key
    parser.add_argument("--pixabay_key", help="Pixabay API key (optional, can use PIXABAY_API_KEY env variable)")
    
    return parser.parse_args()

def setup_directories(temp_dir):
    """Create necessary directories if they don't exist."""
    # Ensure temp_dir doesn't have duplicate path elements and uses consistent separators
    temp_dir = os.path.normpath(temp_dir)
    
    # Print the actual directory paths for debugging
    print(f"Setting up directories with base temp_dir: {temp_dir}")
    
    os.makedirs(temp_dir, exist_ok=True)
    
    wiki_content_dir = os.path.join(temp_dir, "wiki_content")
    images_dir = os.path.join(temp_dir, "images")
    audio_dir = os.path.join(temp_dir, "audio")
    subtitles_dir = os.path.join(temp_dir, "subtitles")
    
    print(f"Creating directory structure:")
    print(f"- Wiki content: {wiki_content_dir}")
    print(f"- Images: {images_dir}")
    print(f"- Audio: {audio_dir}")
    print(f"- Subtitles: {subtitles_dir}")
    
    os.makedirs(wiki_content_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(subtitles_dir, exist_ok=True)
    
    # Normalize all paths for consistency
    return {
        "temp_dir": normalize_path(temp_dir),
        "wiki_content_dir": normalize_path(wiki_content_dir),
        "images_dir": normalize_path(images_dir),
        "audio_dir": normalize_path(audio_dir),
        "subtitles_dir": normalize_path(subtitles_dir)
    }

def fetch_wiki_content(links, temp_dir):
    """Fetch content from Wikipedia using wiki_grabber.py."""
    all_content = []
    
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
            content_file = os.path.join(temp_dir, "wiki_content", f"wiki_{i}.txt")
            with open(content_file, "w", encoding="utf-8") as f:
                f.write(text_content)
            
            all_content.append({
                "title": page_title,
                "content": text_content,
                "file": content_file
            })
        else:
            print(f"Failed to retrieve Wikipedia content for: {page_title}")
    
    return all_content, []  # Return empty list for images
    
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

# Modify the create_narration function to support test narration
def create_narration(script, temp_dir, use_test_narration=False, test_audio_dir="test_audio"):
    """Create narration using narrate.py module or test audio files."""
    # Define output narration file path
    narration_file = os.path.join(temp_dir, "audio", "narration.mp3")
    
    # Write script to file regardless of narration method
    script_file = os.path.join(temp_dir, "script.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(script)
    
    # Check if we should use test narration
    if use_test_narration:
        print("Using test narration instead of ElevenLabs API...")
        
        # Find a test audio file
        test_audio_file = find_first_audio_file(test_audio_dir)
        
        if test_audio_file:
            # Copy the test audio file to the narration file location
            import shutil
            os.makedirs(os.path.dirname(narration_file), exist_ok=True)
            shutil.copy2(test_audio_file, narration_file)
            print(f"Using test audio file: {test_audio_file}")
            return narration_file
        else:
            print("No test audio files found. Falling back to ElevenLabs...")
    
    # If we're not using test narration or no test files were found, use ElevenLabs
    from narrate import narrate_text
    
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

# Helper function to find the first audio file in a directory
def find_first_audio_file(directory):
    """Find the first audio file in a directory."""
    if not os.path.exists(directory):
        print(f"Warning: Test audio directory {directory} does not exist.")
        return None
    
    valid_extensions = ['.mp3', '.wav', '.m4a', '.aac']
    
    for file in os.listdir(directory):
        for ext in valid_extensions:
            if file.lower().endswith(ext):
                return os.path.join(directory, file)
    
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
    
    subtitle_file = os.path.join(temp_dir, "subtitles", "subtitles.srt")
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

def try_add_subtitles(video_with_audio, subtitle_file, output_file, temp_dir):
    """Try different methods to add subtitles to the video."""
    # First ensure all paths are normalized
    video_with_audio = normalize_path(video_with_audio)
    subtitle_file = normalize_path(subtitle_file)
    output_file = normalize_path(output_file)
    temp_dir = normalize_path(temp_dir)
    
    # Try method 1: Using subtitles filter with simplified options
    try:
        print("Trying subtitle method 1...")
        
        # Create a clean copy of the subtitle file with a simple filename in temp directory
        simple_sub_filename = "simple_subs.srt"
        simple_sub_file = os.path.join(temp_dir, simple_sub_filename)
        simple_sub_file = normalize_path(simple_sub_file)
        
        import shutil
        shutil.copy2(subtitle_file, simple_sub_file)
        
        # Properly escape the subtitle path for FFmpeg
        escaped_sub_path = escape_path_for_ffmpeg(simple_sub_file)
        
        # Use a simpler subtitle filter syntax
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", video_with_audio, 
            "-vf", f"subtitles='{escaped_sub_path}'", 
            "-c:a", "copy", output_file
        ]
        
        print(f"Debug - Subtitle command: {' '.join(ffmpeg_cmd)}")
        subprocess.run(ffmpeg_cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"First subtitle method failed: {e}")
        print("Trying method 2...")
        
        # Try method 2: Hardcode the subtitles into the video with ASS format
        try:
            # Convert SRT to ASS (Advanced SubStation Alpha)
            ass_subtitle = os.path.join(temp_dir, "subtitles.ass")
            ass_subtitle = normalize_path(ass_subtitle)
            
            # First create a simple ASS file from the SRT
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", subtitle_file, ass_subtitle
            ]
            subprocess.run(ffmpeg_cmd, check=True)
            
            # Escape ASS path properly
            escaped_ass_path = escape_path_for_ffmpeg(ass_subtitle)
            
            # Then hardcode the ASS subtitles
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", video_with_audio, 
                "-vf", f"ass='{escaped_ass_path}'", 
                "-c:a", "copy", output_file
            ]
            
            print(f"Debug - ASS subtitle command: {' '.join(ffmpeg_cmd)}")
            subprocess.run(ffmpeg_cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Second subtitle method failed: {e}")
            print("Trying method 3 (no styling)...")
            
            # Try method 3: Simplest possible approach with no styling
            # Try to avoid filter complexity
            try:
                # Create a very simple filter with minimal options
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", video_with_audio, 
                    "-vf", "subtitles=" + simple_sub_file.replace('\\', '/').replace(':', '\\:'), 
                    "-c:a", "copy", output_file
                ]
                
                print(f"Debug - Simplified subtitle command: {' '.join(ffmpeg_cmd)}")
                subprocess.run(ffmpeg_cmd, check=True)
                return True
            except subprocess.CalledProcessError as e:
                print(f"Third subtitle method failed: {e}")
                
                # Try method 4: Use a temporary copy in the root directory
                try:
                    # Copy subtitle to current directory to minimize path issues
                    import os
                    current_dir_subs = "current_dir_subs.srt"
                    shutil.copy2(subtitle_file, current_dir_subs)
                    
                    ffmpeg_cmd = [
                        "ffmpeg", "-y", "-i", video_with_audio, 
                        "-vf", f"subtitles={current_dir_subs}", 
                        "-c:a", "copy", output_file
                    ]
                    
                    print(f"Debug - Current directory subtitle command: {' '.join(ffmpeg_cmd)}")
                    subprocess.run(ffmpeg_cmd, check=True)
                    
                    # Clean up the temporary file
                    if os.path.exists(current_dir_subs):
                        os.remove(current_dir_subs)
                        
                    return True
                except subprocess.CalledProcessError as e:
                    print(f"Fourth subtitle method failed: {e}")
                    print("All subtitle methods failed. Creating video without subtitles.")
                    
                    # Fall back to no subtitles if all methods fail
                    import shutil
                    shutil.copy2(video_with_audio, output_file)
                    return False

# Replace the create_video_with_segments function with this improved version
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
        
        # Normalize paths for FFmpeg compatibility
        images = normalize_path_list(images)
        
        # Create a file with image transitions
        image_list_file = normalize_path(os.path.join(temp_dir, "image_list.txt"))
        with open(image_list_file, "w", encoding="utf-8") as f:
            for i, (image, duration) in enumerate(zip(images, paragraph_durations)):
                # Ensure image path is absolute and properly formatted
                img_path = normalize_path(os.path.abspath(image))
                # Escape single quotes in path
                img_path = img_path.replace("'", "'\\''")
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {duration}\n")
            
            # Add last image
            img_path = normalize_path(os.path.abspath(images[-1]))
            img_path = img_path.replace("'", "'\\''")
            f.write(f"file '{img_path}'\n")
        
        # Create the video with images
        print("Creating video with images...")
        video_temp = os.path.join(temp_dir, "temp_video.mp4")
        video_temp = normalize_path(video_temp)
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", image_list_file,
            "-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", video_temp
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Add audio to the video
        print("Adding narration to video...")
        video_with_audio = os.path.join(temp_dir, "video_with_audio.mp4")
        video_with_audio = normalize_path(video_with_audio)
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", video_temp, "-i", narration_file,
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-shortest", video_with_audio
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Add subtitles to the video
        print("Adding subtitles to video...")
        subtitle_file = normalize_path(subtitle_file)
        output_file = normalize_path(output_file)
        
        # Try different subtitle methods with the improved function
        subtitle_success = try_add_subtitles(video_with_audio, subtitle_file, output_file, temp_dir)
        
        if subtitle_success:
            print(f"Video created successfully with subtitles: {output_file}")
        else:
            print(f"Video created without subtitles: {output_file}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error creating video: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

# Also update the create_video function with similar fixes
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
        
        # Normalize paths
        images = normalize_path_list(images)
        
        # Create a file with image transitions
        image_list_file = normalize_path(os.path.join(temp_dir, "image_list.txt"))
        with open(image_list_file, "w", encoding="utf-8") as f:
            images_count = len(images)
            duration_per_image = audio_duration / images_count
            
            for i, image in enumerate(images):
                # Ensure image path is absolute and properly formatted
                img_path = normalize_path(os.path.abspath(image))
                # Escape single quotes in path
                img_path = img_path.replace("'", "'\\''")
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {duration_per_image}\n")
            
            # Add last image
            img_path = normalize_path(os.path.abspath(images[-1]))
            img_path = img_path.replace("'", "'\\''")
            f.write(f"file '{img_path}'\n")
        
        # Create the video with images
        print("Creating video with images...")
        video_temp = normalize_path(os.path.join(temp_dir, "temp_video.mp4"))
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", image_list_file,
            "-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", video_temp
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Add audio to the video
        print("Adding narration to video...")
        video_with_audio = normalize_path(os.path.join(temp_dir, "video_with_audio.mp4"))
        narration_file = normalize_path(narration_file)
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", video_temp, "-i", narration_file,
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-shortest", video_with_audio
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Add subtitles to the video using our improved function
        print("Adding subtitles to video...")
        subtitle_file = normalize_path(subtitle_file)
        output_file = normalize_path(output_file)
        
        subtitle_success = try_add_subtitles(video_with_audio, subtitle_file, output_file, temp_dir)
        
        if subtitle_success:
            print(f"Video created successfully with subtitles: {output_file}")
        else:
            print(f"Video created without subtitles: {output_file}")
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error creating video: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    
# 4. Add this new function to support precise image timing based on durations
def create_video_with_segments_and_durations(title, narration_file, subtitle_file, images, output_file, temp_dir, image_durations=None):
    """
    Create a video with precise image timing based on segment durations.
    
    Args:
        title (str): Video title
        narration_file (str): Path to narration audio file
        subtitle_file (str): Path to subtitle file
        images (list): List of image paths
        output_file (str): Path to output video file
        temp_dir (str): Directory for temporary files
        image_durations (list): List of durations for each image in seconds
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not images:
        print("No images available for the video.")
        return False
    
    try:
        # Determine audio duration for reference
        ffprobe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", narration_file
        ]
        audio_duration = float(subprocess.check_output(ffprobe_cmd).decode('utf-8').strip())
        
        # Normalize paths for FFmpeg compatibility
        images = normalize_path_list(images)
        
        # Create a file with image transitions
        image_list_file = normalize_path(os.path.join(temp_dir, "image_list.txt"))
        with open(image_list_file, "w", encoding="utf-8") as f:
            # If we have explicit durations, use those
            if image_durations and len(image_durations) == len(images):
                for i, (image, duration) in enumerate(zip(images, image_durations)):
                    # Ensure image path is absolute and properly formatted
                    img_path = normalize_path(os.path.abspath(image))
                    # Escape single quotes in path
                    img_path = img_path.replace("'", "'\\''")
                    f.write(f"file '{img_path}'\n")
                    f.write(f"duration {duration}\n")
                
                # Add last image
                img_path = normalize_path(os.path.abspath(images[-1]))
                img_path = img_path.replace("'", "'\\''")
                f.write(f"file '{img_path}'\n")
            else:
                # Fall back to even distribution if no durations provided
                images_count = len(images)
                duration_per_image = audio_duration / images_count
                
                for i, image in enumerate(images):
                    # Ensure image path is absolute and properly formatted
                    img_path = normalize_path(os.path.abspath(image))
                    # Escape single quotes in path
                    img_path = img_path.replace("'", "'\\''")
                    f.write(f"file '{img_path}'\n")
                    f.write(f"duration {duration_per_image}\n")
                
                # Add last image
                img_path = normalize_path(os.path.abspath(images[-1]))
                img_path = img_path.replace("'", "'\\''")
                f.write(f"file '{img_path}'\n")
        
        # Create the video with images
        print("Creating video with precisely timed images...")
        video_temp = os.path.join(temp_dir, "temp_video.mp4")
        video_temp = normalize_path(video_temp)
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", image_list_file,
            "-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", video_temp
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Add audio to the video
        print("Adding narration to video...")
        video_with_audio = os.path.join(temp_dir, "video_with_audio.mp4")
        video_with_audio = normalize_path(video_with_audio)
        narration_file = normalize_path(narration_file)
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", video_temp, "-i", narration_file,
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-shortest", video_with_audio
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Add subtitles to the video using our improved function
        print("Adding subtitles to video...")
        subtitle_file = normalize_path(subtitle_file)
        output_file = normalize_path(output_file)
        
        subtitle_success = try_add_subtitles(video_with_audio, subtitle_file, output_file, temp_dir)
        
        if subtitle_success:
            print(f"Video created successfully with subtitles: {output_file}")
        else:
            print(f"Video created without subtitles: {output_file}")
        
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
    directories = setup_directories(args.temp_dir)
    
    # Fetch Wikipedia content for the script only (no images)
    wiki_contents, _ = fetch_wiki_content(args.links, args.temp_dir)
    
    if not wiki_contents:
        print("No Wikipedia content could be retrieved. Exiting.")
        return
    
    # Generate script
    script = generate_script(args.title, wiki_contents, args.length)
    script_file = os.path.join(args.temp_dir, "script.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"Script saved to {script_file}")
    
    # Split script into paragraphs for better video timing
    paragraphs = split_script_into_paragraphs(script)
    print(f"Script split into {len(paragraphs)} paragraphs for timing")
    
    # Create narration (with test narration support)
    narration_file = create_narration(
        script, 
        args.temp_dir, 
        use_test_narration=args.test_narration,
        test_audio_dir=args.test_audio_dir
    )
    
    if not narration_file:
        print("Failed to create narration. Exiting.")
        return
    
    # Generate subtitles
    subtitle_file = generate_subtitles(narration_file, script, args.temp_dir)
    
    # Get images from Pixabay based on script content
    print("Getting relevant images from Pixabay based on script content...")
    try:
        image_paths, image_durations, segments = get_relevant_images_for_script(
            script_file,
            subtitle_file,
            directories['images_dir'],
            args.pixabay_key
        )
        
        if not image_paths:
            print("No images found from Pixabay. Exiting.")
            return
            
        print(f"Found {len(image_paths)} relevant images for the video.")
        
        # Save segments data for reference
        segments_file = os.path.join(directories['temp_dir'], "segments.json")
        with open(segments_file, "w", encoding="utf-8") as f:
            json.dump(segments, f, indent=2)
            
    except Exception as e:
        print(f"Error getting Pixabay images: {e}")
        return
    
    # Create a base video without title cards
    base_output = normalize_path(os.path.join(args.temp_dir, "base_video.mp4"))
    
    # Create the video with precise image timing based on segments
    success = create_video_with_segments_and_durations(
        args.title, narration_file, subtitle_file, 
        image_paths, base_output, args.temp_dir,
        image_durations=image_durations
    )
    
    if not success:
        print("Video creation failed. Trying simpler approach...")
        # Fallback to simpler video creation if the advanced method fails
        success = create_video(
            args.title, narration_file, subtitle_file, 
            image_paths, base_output, args.temp_dir
        )
        
        if not success:
            print("Video creation failed with both methods. Creating video without subtitles...")
            # Create video with just images and audio as last resort
            try:
                video_with_audio = os.path.join(args.temp_dir, "video_with_audio.mp4")
                if os.path.exists(video_with_audio):
                    import shutil
                    shutil.copy2(video_with_audio, base_output)
                    success = True
                    print(f"Created video without subtitles: {base_output}")
            except Exception as e:
                print(f"Final fallback video creation also failed: {e}")
                return
    
    # Add title cards if not disabled
    if args.no_title_cards:
        print("Title cards disabled, using base video as final output.")
        import shutil
        shutil.copy(base_output, args.output)
        print(f"Video creation complete. Output file: {args.output}")
    else:
        try:
            from title_cards import add_title_cards_to_video
            print("Adding title cards to video...")
            
            # Create a concat list file with absolute paths
            concat_list = os.path.join(args.temp_dir, "concat_list.txt")
            intro_video = os.path.join(args.temp_dir, "intro.mp4")
            outro_video = os.path.join(args.temp_dir, "outro.mp4")
            
            # Ensure all paths are absolute and normalized
            base_output = os.path.abspath(base_output)
            intro_video = os.path.abspath(intro_video)
            outro_video = os.path.abspath(outro_video)
            
            # Call the function with absolute paths
            final_video = add_title_cards_to_video(
                base_output, 
                args.title, 
                os.path.abspath(args.temp_dir), 
                os.path.abspath(args.output)
            )
            print(f"Final video with title cards created: {args.output}")
        except Exception as e:
            print(f"Error adding title cards: {e}")
            print("Using video without title cards as final output.")
            import shutil
            shutil.copy(base_output, args.output)
            print(f"Video creation complete. Output file: {args.output}")
            
if __name__ == "__main__":
    main()