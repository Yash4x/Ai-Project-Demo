"""
📖 CHAPTER 5: THE APPLICATION - Image Generation CLI
=====================================================

STORY: The Grand Finale
------------------------
We've built all the pieces:
- Models (the blueprints) - Chapter 1
- Client (the messenger) - Chapter 2  
- Parser (the translator) - Chapter 3
- Service (the orchestrator) - Chapter 4

Now we need a way for USERS to interact with our system. That's the Application!

Think of this like the front desk at a hotel:
- Guest walks up → "I'd like to generate an image"
- Clerk validates → "What would you like to create?"
- Clerk coordinates → Calls the service to handle the request
- Clerk presents results → Shows the generated image location

This is the "presentation layer" - it handles:
- Command-line arguments (what the user wants)
- User feedback (progress, errors, success)
- Output formatting (making results readable)
- Error handling (explaining what went wrong)

LEARNING OBJECTIVES:
-------------------
✓ Understand CLI design and user experience
✓ Learn argument parsing and validation
✓ Master error handling and user feedback
✓ See how to coordinate all application layers
✓ Appreciate the full application architecture
"""

import os
import sys
import argparse
from typing import Optional

from dotenv import load_dotenv

from src.search_service import ImageGenerationService
from src.parser import ImageResponseParser
from src.models import ImageOptions, ImageResult, ImageError, StoryOptions
from src.logging_config import setup_logging, get_logger, LogContext


# Load environment variables
load_dotenv()

# Initialize logging
app_logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_dir=os.getenv("LOG_DIR", "logs"),
    enable_console=True,
    enable_file=True,
    json_format=os.getenv("LOG_FORMAT", "text").lower() == "json"
)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for image generation.
    
    📚 CONCEPT: Command-Line Interface Design
    -----------------------------------------
    A good CLI should be:
    - Intuitive (obvious what each argument does)
    - Consistent (follows common patterns)
    - Helpful (good help text and examples)
    - Forgiving (sensible defaults)
    
    🎯 DESIGN DECISIONS:
    -------------------
    - Required: prompt (the main thing users want to do)
    - Optional: all technical details (most users want simple defaults)
    - Descriptive: help text explains what each option does
    - Examples: show common usage patterns
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="AI Image Generator - Create images from text prompts using DALL-E",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "A cat wearing a space helmet"                    # Single image generation
  %(prog)s "Sunset over mountains" --model dall-e-2         # Use DALL-E 2 model
  %(prog)s "Abstract art" --save-path ./my_image.png        # Custom save location
  %(prog)s "A robot" --no-save                              # Don't save locally
  
Story Mode:
  %(prog)s "A cat going to shop for watermelons" --story    # Generate 5-scene story
  %(prog)s "Dragon adventure" --story --scenes 3            # Custom number of scenes
        """
    )
    
    # Required: The prompt
    parser.add_argument(
        "prompt",
        type=str,
        help="Text prompt describing the image to generate"
    )
    
    # Optional: Model selection
    parser.add_argument(
        "--model",
        type=str,
        default="dall-e-3",
        choices=["dall-e-2", "dall-e-3"],
        help="AI model to use (default: dall-e-3)"
    )
    
    # Optional: Image size
    parser.add_argument(
        "--size",
        type=str,
        default="1024x1024",
        help="Image size: '1024x1024', '1792x1024', '1024x1792' (DALL-E 3) or '256x256', '512x512', '1024x1024' (DALL-E 2)"
    )
    
    # Optional: Quality (DALL-E 3 only)
    parser.add_argument(
        "--quality",
        type=str,
        default="standard",
        choices=["standard", "hd"],
        help="Image quality for DALL-E 3 (default: standard)"
    )
    
    # Optional: Style (DALL-E 3 only)
    parser.add_argument(
        "--style",
        type=str,
        default="vivid",
        choices=["vivid", "natural"],
        help="Image style for DALL-E 3 (default: vivid)"
    )
    
    # Optional: Response format
    parser.add_argument(
        "--format",
        type=str,
        default="url",
        choices=["url", "b64_json"],
        help="Response format: 'url' for image URL or 'b64_json' for base64 data (default: url)"
    )
    
    # Optional: Custom save path (overrides auto-generated path)
    parser.add_argument(
        "--save-path",
        type=str,
        help="Custom path to save the image (default: auto-generated in ./generated_images/)"
    )
    
    # Optional: Disable auto-save
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't automatically download and save the image locally"
    )
    
    # Optional: Verbose output
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output with detailed information"
    )
    
    # Optional: API key override
    parser.add_argument(
        "--api-key",
        type=str,
        help="OpenAI API key (can also use OPENAI_API_KEY env var)"
    )
    
    # Story generation mode
    parser.add_argument(
        "--story",
        action="store_true",
        help="Generate a visual story (5 sequential images) instead of a single image"
    )
    
    # Number of scenes in story
    parser.add_argument(
        "--scenes",
        type=int,
        default=5,
        help="Number of scenes to generate for story mode (default: 5)"
    )
    
    return parser.parse_args()


def display_results(result: ImageResult, verbose: bool = False) -> None:
    """
    Display image generation results to the user.
    
    📚 CONCEPT: User Experience Design
    ----------------------------------
    This function is all about making the user happy. It should:
    - Show the most important info first (success/failure)
    - Present technical details clearly
    - Guide users on next steps
    - Handle both success and error cases gracefully
    
    Args:
        result: The image generation result to display
        verbose: Whether to show detailed information
    """
    parser = ImageResponseParser()
    formatted = parser.format_for_display(result)
    print(formatted)
    
    # In verbose mode, show additional technical details
    if verbose:
        print("\nTechnical Details:")
        print(f"Generation ID: {result.generation_id}")
        print(f"Timestamp: {result.timestamp}")
        if result.metadata:
            print(f"Model: {result.metadata.model}")
            print(f"Size: {result.metadata.size}")
            if result.metadata.quality:
                print(f"Quality: {result.metadata.quality}")
            if result.metadata.style:
                print(f"Style: {result.metadata.style}")
        
        if result.file_size:
            print(f"File size: {result.file_size:,} bytes")


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate command-line arguments for consistency.
    
    📚 CONCEPT: Input Validation
    ----------------------------
    Some combinations of arguments don't make sense. It's better to catch
    these early and give clear error messages than to let users waste time
    and API credits on invalid requests.
    
    Args:
        args: Parsed command-line arguments
        
    Raises:
        ValueError: If arguments are invalid or inconsistent
    """
    # Validate size based on model
    if args.model == "dall-e-2":
        valid_sizes = ["256x256", "512x512", "1024x1024"]
        if args.size not in valid_sizes:
            raise ValueError(
                f"Invalid size '{args.size}' for DALL-E 2. "
                f"Valid sizes: {', '.join(valid_sizes)}"
            )
    elif args.model == "dall-e-3":
        valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]
        if args.size not in valid_sizes:
            raise ValueError(
                f"Invalid size '{args.size}' for DALL-E 3. "
                f"Valid sizes: {', '.join(valid_sizes)}"
            )
    
    # DALL-E 2 doesn't support quality or style
    if args.model == "dall-e-2":
        if args.quality != "standard":
            raise ValueError("Quality setting only supported for DALL-E 3")
        if args.style != "vivid":
            raise ValueError("Style setting only supported for DALL-E 3")
    
    # Validate save path if provided (but it's optional now)
    if args.save_path:
        import os
        save_dir = os.path.dirname(args.save_path)
        if save_dir and not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except OSError as e:
                raise ValueError(f"Cannot create save directory '{save_dir}': {e}")


def display_story_results(story_result, verbose: bool = False) -> None:
    """
    Display story generation results to the user.
    
    Args:
        story_result: StoryResult object containing all scenes
        verbose: Whether to show detailed information
    """
    print(f"\n🎭 STORY: {story_result.story_prompt}")
    print("=" * 60)
    
    for scene in story_result.scenes:
        print(f"\n📖 Scene {scene.scene_number}: {scene.narrative}")
        
        if scene.is_generated and scene.image_result:
            print(f"✅ Generated: {scene.image_result.image_url}")
            
            if verbose and scene.image_result.metadata:
                print(f"   Model: {scene.image_result.metadata.model}")
                print(f"   Size: {scene.image_result.metadata.size}")
                if scene.image_result.metadata.revised_prompt:
                    print(f"   Revised: {scene.image_result.metadata.revised_prompt}")
                if scene.image_result.metadata.saved_filename:
                    print(f"   Saved: {scene.image_result.metadata.saved_filename}")
        else:
            print("❌ Generation failed")
    
    print(f"\n📊 Summary:")
    print(f"   Success Rate: {story_result.success_rate:.1f}%")
    print(f"   Total Time: {story_result.total_generation_time:.2f}s")


def main() -> int:
    """
    Main application entry point for image generation.
    
    📚 CONCEPT: Application Architecture
    ------------------------------------
    This is the "conductor" of our application orchestra. It coordinates:
    1. Argument parsing (what does the user want?)
    2. Validation (is the request valid?)
    3. Service initialization (set up our tools)
    4. Business logic execution (do the work)
    5. Result presentation (show the user what happened)
    6. Error handling (what if something goes wrong?)
    
    🎯 ERROR HANDLING STRATEGY:
    ---------------------------
    - Expected errors (ImageError) → user-friendly messages
    - Input errors (ValueError) → helpful validation messages  
    - Unexpected errors (Exception) → technical details for debugging
    - User cancellation (KeyboardInterrupt) → graceful exit
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger = get_logger(__name__)
    
    try:
        # Log application start
        logger.info("Image generation application started")
        
        # Parse command line arguments
        args = parse_arguments()
        logger.debug(
            f"Parsed arguments: prompt='{args.prompt}', "
            f"model={args.model}, size={args.size}"
        )
        
        # Validate arguments
        validate_arguments(args)
        
        # Verbose logging
        if args.verbose:
            print(f"🎨 Generating image with DALL-E...")
            print(f"Model: {args.model}")
            print(f"Size: {args.size}")
            print(f"Prompt: {args.prompt}")
            if args.save_path:
                print(f"Custom save path: {args.save_path}")
            elif not args.no_save:
                print(f"Auto-save: ./generated_images/")
            else:
                print(f"Save: Disabled")
            print()
        
        # Create image options
        options = ImageOptions(
            model=args.model,
            size=args.size,
            quality=args.quality,
            style=args.style,
            response_format=args.format
        )
        logger.debug(f"Created image options: {options}")
        
        # Get API key (try argument first, then environment)
        api_key = args.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI API key not provided")
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or use --api-key argument"
            )
        
        # Initialize service
        logger.debug("Initializing image generation service")
        service = ImageGenerationService(api_key=api_key)
        
        # Check if this is story mode or single image mode
        if args.story:
            # Story generation mode
            if args.verbose:
                print(f"🎬 Generating story with {args.scenes} scenes...")
            
            # Create story options
            story_options = StoryOptions(
                story_prompt=args.prompt,
                num_scenes=args.scenes,
                model=args.model,
                size=args.size,
                quality=args.quality,
                style=args.style,
                auto_save=not args.no_save,
                save_path=args.save_path
            )
            
            logger.info(f"Executing story generation: '{args.prompt}' with {args.scenes} scenes")
            with LogContext(logger, "Story generation", prompt=args.prompt, scenes=args.scenes):
                story_result = service.generate_story(story_options)
            
            logger.info(f"Story generation completed: {len(story_result.completed_scenes)}/{args.scenes} scenes")
            
            # Display story results
            display_story_results(story_result, verbose=args.verbose)
            
            # Show helpful information
            if story_result.completed_scenes:
                saved_files = story_result.get_scene_filenames()
                if saved_files:
                    # Check if files are in a story folder
                    first_file = saved_files[0]
                    if "story_" in first_file:
                        # Extract the story folder from the first file path
                        story_folder = os.path.dirname(first_file)
                        print(f"\n✅ Story images saved in: {story_folder}")
                        print(f"📁 Scene files:")
                        for filename in saved_files:
                            print(f"   • {os.path.basename(filename)}")
                    else:
                        print(f"\n✅ Story images saved:")
                        for filename in saved_files:
                            print(f"   • {filename}")
                else:
                    print(f"\n💡 Story images available online (not saved locally):")
                    for i, url in enumerate(story_result.all_image_urls, 1):
                        print(f"   • Scene {i}: {url}")
                    print(f"   • Note: URLs expire in a few hours")
                    print(f"   • Next time: remove --no-save to auto-download")
            
            if story_result.failed_scenes:
                print(f"\n⚠️  {len(story_result.failed_scenes)} scene(s) failed to generate")
        
        else:
            # Single image generation mode
            if args.verbose:
                print("🚀 Generating image...")
            
            logger.info(f"Executing image generation: '{args.prompt}'")
            with LogContext(logger, "Image generation", prompt=args.prompt, model=args.model):
                if args.save_path:
                    # User provided custom save path - use generate_and_save
                    result = service.generate_and_save(args.prompt, args.save_path, options)
                else:
                    # Use auto-save behavior (unless disabled)
                    auto_save = not args.no_save
                    result = service.generate_image(args.prompt, options, auto_save=auto_save)
            
            logger.info(f"Image generation completed: {result.generation_id}")
            
            # Display results
            display_results(result, verbose=args.verbose)
            
            # Show helpful information based on what happened
            if result.is_saved:
                print(f"\n✅ Image saved to: {result.file_path}")
                print(f"💡 You can also view it online: {result.image_url}")
            elif result.image_url:
                print(f"\n💡 Image available online (not saved locally):")
                print(f"   • Visit: {result.image_url}")
                print(f"   • Note: URL expires in a few hours")
                print(f"   • Next time: remove --no-save to auto-download")
        
        logger.info("Image generation application completed successfully")
        return 0
        
    except ImageError as e:
        # Image generation specific errors
        logger.error(f"Image generation error: {e}", exc_info=True)
        print(f"\n❌ Image Generation Error: {e}", file=sys.stderr)
        
        # Provide helpful hints based on error type
        if e.code == "CONTENT_POLICY_ERROR":
            print("💡 Try rephrasing your prompt to avoid potentially problematic content.", file=sys.stderr)
        elif e.code == "RATE_LIMIT_ERROR":
            print("💡 Wait a moment and try again. Consider upgrading your OpenAI plan.", file=sys.stderr)
        elif e.code == "AUTHENTICATION_ERROR":
            print("💡 Check your API key. Visit https://platform.openai.com/api-keys", file=sys.stderr)
        
        return 1
        
    except ValueError as e:
        # Input validation errors
        logger.error(f"Invalid input: {e}", exc_info=True)
        print(f"\n❌ Invalid Input: {e}", file=sys.stderr)
        print("💡 Use --help to see valid options.", file=sys.stderr)
        return 1
        
    except KeyboardInterrupt:
        logger.warning("Image generation cancelled by user (KeyboardInterrupt)")
        print("\n\n🛑 Generation cancelled by user.", file=sys.stderr)
        return 130
        
    except Exception as e:
        # Defensive fallback for unexpected errors
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected Error: {e}", file=sys.stderr)
        if 'args' in locals() and args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
