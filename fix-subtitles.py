#!/usr/bin/env python3
# fix_subtitles.py - Standalone script to fix subtitles in video

import os
import subprocess
import argparse
import re
import shutil
from pathlib import Path

def normalize_path(path):
    """Normalize path for FFmpeg compatibility."""
    return os.path.abspath(path).replace('\\', '/')

def format_time(seconds):
    """Format time in SRT format: HH:MM:SS,mmm."""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds_int = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"

def get_audio_duration(audio_file):
    """Get duration of audio file in seconds."""
    try:
        ffprobe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_file
        ]
        return float(subprocess.check_output(ffprobe_cmd).decode('utf-8').strip())
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return 0

def create_subtitles_for_audio(script_text, audio_file, output_file):
    """Create SRT subtitles that match the audio duration."""
    # Get audio duration
    audio_duration = get_audio_duration(audio_file)
    if audio_duration <= 0:
        print("Could not determine audio duration. Using default timing.")
        audio_duration = len(script_text) / 15  # Assume 15 chars per second
    
    # Split into sentences or manageable segments
    sentences = re.split(r'(?<=[.!?])\s+', script_text)
    
    # Create subtitle content
    current_time = 0
    subtitle_content = ""
    subtitle_count = 1
    
    # Calculate time per sentence based on relative length
    total_chars = sum(len(s) for s in sentences)
    
    for sentence in sentences:
        if not sentence.strip():
            continue
            
        # Calculate timing for this sentence
        char_ratio = len(sentence) / total_chars
        duration = audio_duration * char_ratio
        end_time = current_time + duration
        
        # Format in SRT format
        subtitle_content += f"{subtitle_count}\n"
        subtitle_content += f"{format_time(current_time)} --> {format_time(end_time)}\n"
        subtitle_content += f"{sentence.strip()}\n\n"
        
        subtitle_count += 1
        current_time = end_time
    
    # Write to file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(subtitle_content)
    
    print(f"Created subtitles matched to audio: {output_file}")
    return output_file

def add_subtitles_to_video(video_file, subtitle_file, output_file):
    """Add subtitles to video with multiple fallback methods."""
    video_file = normalize_path(video_file)
    subtitle_file = normalize_path(subtitle_file)
    output_file = normalize_path(output_file)
    
    # Method 1: Direct subtitles filter with filtered subtitle path
    try:
        print("\nTrying subtitle method 1...")
        
        # Create a clean copy of the subtitle file with minimal path
        temp_dir = os.path.dirname(output_file)
        simple_sub_file = os.path.join(temp_dir, "simple.srt")
        simple_sub_file = normalize_path(simple_sub_file)
        
        shutil.copy2(subtitle_file, simple_sub_file)
        
        # Use subtitles filter with simple path
        ffmpeg_cmd = [
            "ffmpeg", "-y", 
            "-i", video_file,
            "-vf", f"subtitles={simple_sub_file}",
            "-c:a", "copy", 
            output_file
        ]
        
        print(f"Command: {' '.join(ffmpeg_cmd)}")
        subprocess.run(ffmpeg_cmd, check=True)
        print("Success! Subtitles added to video.")
        return True
    except Exception as e:
        print(f"Method 1 failed: {e}")
    
    # Method 2: Try with full path properly escaped
    try:
        print("\nTrying subtitle method 2...")
        escaped_path = subtitle_file.replace(":", "\\:")
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", 
            "-i", video_file,
            "-vf", f"subtitles={escaped_path}",
            "-c:a", "copy", 
            output_file
        ]
        
        print(f"Command: {' '.join(ffmpeg_cmd)}")
        subprocess.run(ffmpeg_cmd, check=True)
        print("Success! Subtitles added to video.")
        return True
    except Exception as e:
        print(f"Method 2 failed: {e}")
    
    # Method 3: Add subtitles as separate stream
    try:
        print("\nTrying subtitle method 3 (separate stream)...")
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", 
            "-i", video_file,
            "-i", subtitle_file,
            "-c:v", "copy", 
            "-c:a", "copy",
            "-c:s", "mov_text",
            "-metadata:s:s:0", "language=eng",
            output_file
        ]
        
        print(f"Command: {' '.join(ffmpeg_cmd)}")
        subprocess.run(ffmpeg_cmd, check=True)
        print("Success! Subtitles added as separate stream.")
        return True
    except Exception as e:
        print(f"Method 3 failed: {e}")
    
    # Method 4: Create subtitles in current directory
    try:
        print("\nTrying subtitle method 4 (current directory)...")
        
        # Copy files to current directory
        current_dir = os.getcwd()
        current_video = os.path.join(current_dir, "input.mp4")
        current_subs = os.path.join(current_dir, "subs.srt")
        current_output = os.path.join(current_dir, "output.mp4")
        
        shutil.copy2(video_file, current_video)
        shutil.copy2(subtitle_file, current_subs)
        
        # Run FFmpeg with simple paths
        ffmpeg_cmd = [
            "ffmpeg", "-y", 
            "-i", "input.mp4",
            "-vf", "subtitles=subs.srt",
            "-c:a", "copy", 
            "output.mp4"
        ]
        
        print(f"Command: {' '.join(ffmpeg_cmd)}")
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Copy result back and clean up
        shutil.copy2(current_output, output_file)
        
        # Clean up temporary files
        for temp_file in [current_video, current_subs, current_output]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
        print("Success! Subtitles added to video.")
        return True
    except Exception as e:
        print(f"Method 4 failed: {e}")
    
    print("All subtitle methods failed. Could not add subtitles to video.")
    return False

def fix_video_subtitles(video_file, script_file, output_file, temp_dir="temp"):
    """Main function to fix subtitles in a video."""
    # Ensure directories exist
    os.makedirs(temp_dir, exist_ok=True)
    
    # Read the script
    with open(script_file, 'r', encoding='utf-8') as f:
        script_text = f.read()
    
    # Generate subtitles matched to the video
    subtitle_file = os.path.join(temp_dir, "fixed_subtitles.srt")
    create_subtitles_for_audio(script_text, video_file, subtitle_file)
    
    # Add subtitles to video
    print(f"Adding subtitles to video: {video_file}")
    success = add_subtitles_to_video(video_file, subtitle_file, output_file)
    
    if success:
        print(f"Successfully created video with subtitles: {output_file}")
    else:
        print(f"Failed to add subtitles. Copying original video as fallback.")
        shutil.copy2(video_file, output_file)
    
    return success

def find_video_without_subtitles(temp_dir):
    """Find the intermediate video without subtitles."""
    video_candidates = [
        os.path.join(temp_dir, "video_with_audio.mp4"),
        os.path.join(temp_dir, "base_video.mp4")
    ]
    
    for video in video_candidates:
        if os.path.exists(video):
            return video
    
    return None

def main():
    parser = argparse.ArgumentParser(description="Fix subtitles in video_creator.py outputs")
    parser.add_argument("--video", help="Input video file (optional)")
    parser.add_argument("--script", help="Script file (optional)")
    parser.add_argument("--output", default="output_with_subtitles.mp4", help="Output video file")
    parser.add_argument("--temp_dir", default="temp", help="Temp directory")
    
    args = parser.parse_args()
    
    # Find input video if not specified
    video_file = args.video
    if not video_file:
        video_file = find_video_without_subtitles(args.temp_dir)
        if not video_file:
            print("Could not find input video. Please specify with --video.")
            return False
    
    # Find script file if not specified
    script_file = args.script
    if not script_file:
        script_file = os.path.join(args.temp_dir, "script.txt")
        if not os.path.exists(script_file):
            print("Could not find script file. Please specify with --script.")
            return False
    
    print(f"Input video: {video_file}")
    print(f"Script file: {script_file}")
    print(f"Output file: {args.output}")
    
    return fix_video_subtitles(video_file, script_file, args.output, args.temp_dir)

if __name__ == "__main__":
    main()
