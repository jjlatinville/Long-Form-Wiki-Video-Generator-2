#!/usr/bin/env python3
# test_video_creator.py - Run video creation without generating AI content

import os
import argparse
import subprocess
import re
import sys
from pathlib import Path

# Import functions from video_creator.py
sys.path.append('.')
from video_creator import normalize_path, normalize_path_list, create_video_with_segments, setup_directories
from title_cards import add_title_cards_to_video

# Fix for hyphenated filename (title-cards.py)
# If the regular import fails, try with the hyphenated filename
try:
    from title_cards import add_title_cards_to_video
except ModuleNotFoundError:
    # Try to handle hyphenated filename
    import importlib.util
    import sys
    
    # Try to load the module with hyphen
    try:
        spec = importlib.util.spec_from_file_location("title_cards", "title-cards.py")
        title_cards = importlib.util.module_from_spec(spec)
        sys.modules["title_cards"] = title_cards
        spec.loader.exec_module(title_cards)
        add_title_cards_to_video = title_cards.add_title_cards_to_video
        print("Successfully imported title_cards module from title-cards.py")
    except Exception as e:
        print(f"Warning: Could not import title_cards module: {e}")
        # Define a simple replacement function that just copies the input file
        def add_title_cards_to_video(video_path, title, temp_dir, output_path=None):
            import shutil
            output_path = output_path or video_path
            shutil.copy(video_path, output_path)
            print(f"Title cards functionality not available. Copied video without title cards.")
            return output_path

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test video creation without using AI generation.")
    parser.add_argument("--title", default="Test Video", help="Title of the video")
    parser.add_argument("--output", default="test_output_video.mp4", help="Output video filename")
    parser.add_argument("--temp_dir", default="temp", help="Directory for temporary files")
    parser.add_argument("--test_audio", default="test_audio", help="Directory with test audio files")
    parser.add_argument("--test_images", default="test_images", help="Directory with test image files")
    parser.add_argument("--test_subtitles", default="test_subtitles", help="Directory with test subtitle files")
    parser.add_argument("--test_wiki", default="test_wiki_content", help="Directory with test wiki content")
    parser.add_argument("--no-title-cards", action="store_true", help="Disable intro and outro title cards")
    
    return parser.parse_args()

def find_first_file(directory, extensions):
    """Find the first file with one of the given extensions in the directory."""
    if not os.path.exists(directory):
        print(f"Warning: Directory {directory} does not exist.")
        return None
        
    for ext in extensions:
        for file in os.listdir(directory):
            if file.endswith(ext):
                return os.path.join(directory, file)
    return None

def load_test_script(test_wiki_dir):
    """Load test script from the wiki content directory."""
    script_file = find_first_file(test_wiki_dir, [".txt"])
    
    if not script_file:
        # Create a simple default script if none exists
        default_script = "This is a test video script.\n\nIt contains multiple paragraphs.\n\nEach paragraph will be synchronized with an image."
        script_file = os.path.join(test_wiki_dir, "default_script.txt")
        
        os.makedirs(test_wiki_dir, exist_ok=True)
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(default_script)
            
        print(f"Created default script at {script_file}")
        return default_script
    
    with open(script_file, "r", encoding="utf-8") as f:
        return f.read()

def split_script_into_paragraphs(script):
    """Split the script into logical paragraphs for synchronization with images."""
    # First split by double newlines
    paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]
    
    # If we don't have enough paragraphs, try to split by single newlines
    if len(paragraphs) < 3:
        paragraphs = [p.strip() for p in script.split('\n') if p.strip()]
    
    # Ensure we have at least 3 paragraphs for testing
    while len(paragraphs) < 3:
        paragraphs.append(f"Additional test paragraph {len(paragraphs) + 1}.")
    
    return paragraphs

def collect_test_images(test_images_dir):
    """Collect a list of test images from the specified directory."""
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    images = []
    
    if not os.path.exists(test_images_dir):
        print(f"Warning: Test images directory {test_images_dir} does not exist.")
        return []
    
    # Create a list of all image files
    for root, _, files in os.walk(test_images_dir):
        for file in files:
            ext = os.path.splitext(file.lower())[1]
            if ext in valid_extensions:
                images.append(os.path.join(root, file))
    
    if not images:
        print(f"Warning: No images found in {test_images_dir}")
    else:
        print(f"Found {len(images)} test images")
    
    return images

def get_test_audio(test_audio_dir):
    """Get a test audio file from the specified directory."""
    audio_file = find_first_file(test_audio_dir, ['.mp3', '.wav', '.m4a', '.aac'])
    
    if not audio_file:
        print(f"Warning: No audio file found in {test_audio_dir}")
    else:
        print(f"Using test audio file: {audio_file}")
    
    return audio_file

def get_test_subtitles(test_subtitles_dir):
    """Get a test subtitle file from the specified directory."""
    subtitle_file = find_first_file(test_subtitles_dir, ['.srt', '.vtt'])
    
    if not subtitle_file:
        print(f"Warning: No subtitle file found in {test_subtitles_dir}")
    else:
        print(f"Using test subtitle file: {subtitle_file}")
    
    return subtitle_file

def create_default_subtitles(script, temp_dir):
    """Create a simple subtitle file based on the script."""
    # Split the script into sentences
    sentences = re.split(r'(?<=[.!?])\s+', script)
    
    # Create a simple SRT file
    subtitle_content = ""
    current_time = 0
    
    for i, sentence in enumerate(sentences):
        # Estimate 5 seconds per sentence
        start_time = current_time
        end_time = current_time + 5
        current_time = end_time
        
        # Format in SRT format
        subtitle_content += f"{i+1}\n"
        subtitle_content += f"{format_time(start_time)} --> {format_time(end_time)}\n"
        subtitle_content += f"{sentence.strip()}\n\n"
    
    subtitle_file = os.path.join(temp_dir, "subtitles", "default_subtitles.srt")
    os.makedirs(os.path.dirname(subtitle_file), exist_ok=True)
    
    with open(subtitle_file, "w", encoding="utf-8") as f:
        f.write(subtitle_content)
    
    print(f"Created default subtitle file: {subtitle_file}")
    return subtitle_file

def format_time(seconds):
    """Format time in SRT format: HH:MM:SS,mmm."""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds_int = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"

def copy_file_to_temp(source_file, target_dir, target_name):
    """Copy a file to the temp directory."""
    if not source_file or not os.path.exists(source_file):
        return None
    
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, target_name)
    
    # Copy the file
    import shutil
    shutil.copy2(source_file, target_file)
    
    return target_file

def main():
    """Main function to run the video creation test."""
    args = parse_arguments()
    
    print(f"=== Test Video Creator ===")
    print(f"Title: {args.title}")
    print(f"Output: {args.output}")
    
    # Set up directories
    directories = setup_directories(args.temp_dir)
    
    # Load test script
    script = load_test_script(args.test_wiki)
    script_file = os.path.join(directories['temp_dir'], "script.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"Script loaded and saved to {script_file}")
    
    # Split script into paragraphs
    paragraphs = split_script_into_paragraphs(script)
    print(f"Script split into {len(paragraphs)} paragraphs")
    
    # Collect test images
    images = collect_test_images(args.test_images)
    
    # Ensure we have at least one image
    if not images:
        print("Error: No test images found. At least one image is required.")
        return
    
    # If we have fewer images than paragraphs, repeat images
    while len(images) < len(paragraphs):
        images.append(images[len(images) % len(images)])
    
    # Get test audio file
    audio_file = get_test_audio(args.test_audio)
    
    # If no test audio found, we can't proceed
    if not audio_file:
        print("Error: No test audio file found. An audio file is required.")
        return
    
    # Copy the audio file to the temp directory
    narration_file = copy_file_to_temp(
        audio_file, 
        directories['audio_dir'], 
        "narration.mp3"
    )
    
    # Get test subtitle file or create a default one
    subtitle_file = get_test_subtitles(args.test_subtitles)
    if not subtitle_file:
        subtitle_file = create_default_subtitles(script, directories['temp_dir'])
    else:
        # Copy the subtitle file to the temp directory
        subtitle_file = copy_file_to_temp(
            subtitle_file, 
            directories['subtitles_dir'], 
            "subtitles.srt"
        )
    
    # Create a base video without title cards
    base_output = normalize_path(os.path.join(directories['temp_dir'], "base_video.mp4"))
    
    # Create the video with paragraph-based timing
    print("\nCreating video...")
    success = create_video_with_segments(
        args.title, narration_file, subtitle_file, 
        images, paragraphs, base_output, directories['temp_dir']
    )
    
    if not success:
        print("Video creation failed.")
        return
    
    # Add title cards if not disabled
    if args.no_title_cards:
        print("Title cards disabled, using base video as final output.")
        import shutil
        shutil.copy(base_output, args.output)
        print(f"Video creation complete. Output file: {args.output}")
    else:
        try:
            print("Adding title cards to video...")
            final_video = add_title_cards_to_video(base_output, args.title, directories['temp_dir'], args.output)
            print(f"Final video with title cards created: {args.output}")
        except Exception as e:
            print(f"Error adding title cards: {e}")
            print("Using video without title cards as final output.")
            import shutil
            shutil.copy(base_output, args.output)
            print(f"Video creation complete. Output file: {args.output}")

if __name__ == "__main__":
    main()