#!/usr/bin/env python3
# create_custom_video.py - More advanced example script with user input

import argparse
import subprocess
import os
import sys

def main():
    """Interactive script to create custom AI-generated videos."""
    print("\n=== AI Video Creator - Interactive Mode ===\n")
    
    # Get video title
    title = input("Enter your video title: ").strip()
    if not title:
        print("Error: Title cannot be empty")
        return
    
    # Get Wikipedia links
    print("\nEnter Wikipedia URLs (one per line, enter a blank line when done):")
    links = []
    while True:
        link = input("URL: ").strip()
        if not link:
            break
        if "wikipedia.org" not in link:
            print("Warning: This doesn't look like a Wikipedia URL. Include it anyway? (y/n)")
            if input().lower() != 'y':
                continue
        links.append(link)
    
    if not links:
        print("Error: At least one Wikipedia URL is required")
        return
    
    # Get script length
    length = 2000  # Default
    try:
        length_input = input("\nEnter target script length in characters (default: 2000): ").strip()
        if length_input:
            length = int(length_input)
    except ValueError:
        print(f"Warning: Using default length of {length} characters")
    
    # Output file
    output = input("\nEnter output filename (default: output_video.mp4): ").strip()
    if not output:
        output = "output_video.mp4"
    
    # Ask about title cards
    use_title_cards = input("\nAdd intro and outro title cards? (y/n, default: y): ").lower().strip()
    no_title_cards = use_title_cards == 'n'
    
    # Advanced options
    print("\nAdvanced options (press Enter to use defaults):")
    temp_dir = input("Temporary directory (default: temp): ").strip() or "temp"
    
    # Confirm settings
    print("\n=== Video Creation Settings ===")
    print(f"Title: {title}")
    print(f"Links: {len(links)} Wikipedia URLs")
    for i, link in enumerate(links):
        print(f"  {i+1}. {link}")
    print(f"Script length: {length} characters")
    print(f"Output file: {output}")
    print(f"Title cards: {'Disabled' if no_title_cards else 'Enabled'}")
    print(f"Temp directory: {temp_dir}")
    
    confirm = input("\nProceed with these settings? (y/n): ").lower().strip()
    if confirm != 'y':
        print("Video creation cancelled")
        return
    
    # Build the command
    cmd = ["python", "video_creator.py", 
           "--title", title,
           "--length", str(length),
           "--output", output,
           "--temp_dir", temp_dir]
    
    # Add links
    cmd.append("--links")
    cmd.extend(links)
    
    # Add no title cards flag if needed
    if no_title_cards:
        cmd.append("--no-title-cards")
    
    # Execute the command
    print("\nStarting video creation process...")
    print("This may take several minutes depending on the content size and your hardware.")
    print("=" * 50)
    
    try:
        subprocess.run(cmd, check=True)
        print("\nVideo creation process completed!")
        
        output_path = os.path.abspath(output)
        print(f"\nYour video is ready: {output_path}")
        
        # Ask if user wants to play the video
        if sys.platform.startswith('win'):
            player = 'start'
        elif sys.platform.startswith('darwin'):  # macOS
            player = 'open'
        else:  # Linux/Unix
            player = 'xdg-open'
            
        play_video = input("\nDo you want to play the video now? (y/n): ").lower().strip()
        if play_video == 'y':
            try:
                subprocess.run([player, output], shell=True)
            except Exception as e:
                print(f"Could not play video: {e}")
    
    except subprocess.CalledProcessError as e:
        print(f"\nError creating video: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    main()
