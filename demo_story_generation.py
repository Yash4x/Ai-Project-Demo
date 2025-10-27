#!/usr/bin/env python3
"""
Story Generation Demo

This script demonstrates the new story generation feature that creates
5 sequential images to tell a visual story from a text prompt.

Example usage:
  python demo_story_generation.py
"""

import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.search_service import ImageGenerationService
from src.models import StoryOptions

def main():
    """Demo the story generation feature."""
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return 1
    
    print("🎬 Story Generation Demo")
    print("=" * 50)
    print()
    
    # Demo stories
    demo_stories = [
        "A cat going to shop for watermelons",
        "A robot learning to dance", 
        "A dragon discovering friendship",
        "A tiny mouse on a big adventure",
        "A flower growing in space"
    ]
    
    print("Available demo stories:")
    for i, story in enumerate(demo_stories, 1):
        print(f"  {i}. {story}")
    print(f"  {len(demo_stories) + 1}. Enter custom story")
    print()
    
    # Get user choice
    try:
        choice = input("Choose a story (1-6): ").strip()
        
        if choice == str(len(demo_stories) + 1):
            story_prompt = input("Enter your custom story: ").strip()
            if not story_prompt:
                print("❌ Empty story prompt!")
                return 1
        else:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(demo_stories):
                story_prompt = demo_stories[choice_idx]
            else:
                print("❌ Invalid choice!")
                return 1
                
    except (ValueError, KeyboardInterrupt):
        print("\n👋 Goodbye!")
        return 0
    
    # Get number of scenes
    try:
        scenes_input = input(f"Number of scenes (default: 5): ").strip()
        num_scenes = int(scenes_input) if scenes_input else 5
        if num_scenes < 1 or num_scenes > 10:
            print("❌ Number of scenes must be between 1 and 10")
            return 1
    except ValueError:
        print("❌ Invalid number of scenes")
        return 1
    
    print(f"\n🎬 Generating {num_scenes}-scene story: '{story_prompt}'")
    print("This may take a few minutes...")
    print()
    
    # Create story options
    story_options = StoryOptions(
        story_prompt=story_prompt,
        num_scenes=num_scenes,
        model="dall-e-3",
        size="1024x1024",
        auto_save=True
    )
    
    # Generate the story
    try:
        service = ImageGenerationService(api_key=api_key)
        story_result = service.generate_story(story_options)
        
        # Show results
        print("\n" + "=" * 60)
        print(f"🎭 STORY COMPLETE: {story_result.story_prompt}")
        print("=" * 60)
        
        for scene in story_result.scenes:
            print(f"\n📖 Scene {scene.scene_number}: {scene.narrative}")
            if scene.is_generated:
                print(f"✅ Generated successfully")
                if scene.image_result and scene.image_result.file_path:
                    print(f"💾 Saved: {os.path.basename(scene.image_result.file_path)}")
            else:
                print("❌ Generation failed")
        
        print(f"\n📊 Final Results:")
        print(f"   • Success Rate: {story_result.success_rate:.1f}%")
        print(f"   • Total Time: {story_result.total_generation_time:.1f} seconds")
        print(f"   • Images Saved: {len(story_result.get_scene_filenames())}")
        
        if story_result.completed_scenes:
            print(f"\n🎨 View your story images in the generated_images/story_X folder!")
            print(f"📁 Each story gets its own organized folder (story_1, story_2, etc.)")
            
        return 0
        
    except Exception as e:
        print(f"\n❌ Error generating story: {e}")
        return 1

if __name__ == "__main__":
    exit(main())