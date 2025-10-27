"""
📖 CHAPTER 4: THE ORCHESTRATOR - Image Generation Service
==========================================================

STORY: Bringing It All Together
--------------------------------
So far we have created:
- Models (the blueprints) - Chapter 1
- Client (the messenger) - Chapter 2  
- Parser (the translator) - Chapter 3

Now we need someone to coordinate all these pieces. That's the Service!

Think of it like a restaurant kitchen:
- You (the customer) → place an order
- Service (the head chef) → coordinates everything:
  * Validates your order (is this prompt appropriate?)
  * Delegates to specialists (Client talks to OpenAI)
  * Quality control (Parser formats the response)
  * Final presentation (returns clean ImageResult)

The Service is where business logic lives. It doesn't know about:
- ❌ HTTP requests (that's the Client's job)
- ❌ Response parsing (that's the Parser's job)
- ❌ User interface (that's the main app's job)

It DOES know about:
- ✓ Validation rules (what makes a valid prompt?)
- ✓ Error handling (what if generation fails?)
- ✓ Coordination (how to use Client + Parser together)
- ✓ Business decisions (should we download the image?)

LEARNING OBJECTIVES:
-------------------
✓ Understand service layer patterns
✓ Learn business logic separation
✓ Master error handling and validation
✓ See how to coordinate multiple components
✓ Appreciate clean architecture principles
"""

import os
import re
import requests
from typing import Optional
from datetime import datetime

from src.client import ImageGenerationClient
from src.parser import ImageResponseParser
from src.models import ImageOptions, ImageResult, ImageError


class ImageGenerationService:
    """
    Service for coordinating image generation operations.
    
    📚 CONCEPT: The Service Layer Pattern  
    --------------------------------------
    This is the "business logic" layer of our application. It sits between
    the user interface (main.py) and the technical details (client.py, parser.py).
    
    RESPONSIBILITIES:
    1. Validate user input (is the prompt appropriate?)
    2. Coordinate components (client + parser)
    3. Handle errors gracefully
    4. Apply business rules (download policies, etc.)
    5. Provide a clean API for the main application
    
    🎯 REAL-WORLD ANALOGY:
    Think of this like a photo studio manager:
    - Customer says: "I want a portrait"
    - Manager validates: "Do you have ID? Budget approved?"
    - Manager coordinates: Tells photographer what to shoot
    - Manager handles problems: "Camera broke, we'll use backup"
    - Manager delivers: Gives customer finished photos
    
    📝 DESIGN PRINCIPLE: Dependency Inversion
    -----------------------------------------
    Notice we inject the API key rather than hardcoding it. This makes
    the service flexible and testable:
    
    ✅ GOOD: service = ImageGenerationService(api_key=test_key)
    ❌ BAD:  service always uses production API key
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the image generation service.
        
        📚 CONCEPT: Composition over Inheritance
        ----------------------------------------
        Instead of inheriting from Client or Parser, we COMPOSE them.
        This is more flexible because:
        - Easy to swap implementations (different AI providers)
        - Clear separation of concerns
        - Easier to test (can mock individual components)
        
        Args:
            api_key: OpenAI API key
            
        Raises:
            ValueError: If no API key is provided
        """
        if not api_key:
            raise ValueError("API key is required")
        
        # Compose our dependencies
        self.client = ImageGenerationClient(api_key=api_key)
        self.parser = ImageResponseParser()
    
    def generate_image(self, prompt: str, options: Optional[ImageOptions] = None, auto_save: bool = True, save_dir: str = "generated_images") -> ImageResult:
        """
        Generate an image from a text prompt.
        
        📚 CONCEPT: Template Method Pattern
        -----------------------------------
        This method follows the same pattern every time:
        1. Validate input
        2. Set defaults
        3. Call external service
        4. Parse response
        5. Auto-download and save (NEW!)
        6. Handle errors
        
        EXAMPLE USAGE:
        >>> service = ImageGenerationService(api_key="sk-...")
        >>> result = service.generate_image("A space cat")
        >>> print(f"Generated: {result.image_url}")
        >>> print(f"Saved to: {result.file_path}")  # Automatically saved!
        
        Args:
            prompt: Text description of the desired image
            options: Optional generation configuration
            auto_save: Whether to automatically download and save the image (default: True)
            save_dir: Directory to save images in (default: "generated_images")
            
        Returns:
            ImageResult with generated image data and local file path
            
        Raises:
            ValueError: If prompt is invalid
            ImageError: If generation fails
        """
        # Step 1: Validate input
        if not self.validate_prompt(prompt):
            raise ValueError("Invalid prompt: must be non-empty and under 4000 characters")
        
        # Step 2: Set defaults
        if options is None:
            options = ImageOptions()
        
        try:
            # Step 3: Call external service
            raw_response = self.client.generate_image(prompt, options)
            
            # Step 4: Parse response
            result = self.parser.parse(raw_response, prompt)
            
            # Step 5: Auto-download and save (NEW!)
            if auto_save and result.image_url:
                # Generate a safe filename from the prompt
                safe_filename = self._generate_safe_filename(prompt, result.generation_id)
                save_path = os.path.join(save_dir, safe_filename)
                
                # Download and save the image
                result = self.download_and_save_image(result, save_path)
            
            return result
            
        except ImageError:
            # Re-raise our custom errors (they're already well-formatted)
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ImageError(
                code="GENERATION_FAILED",
                message=f"Image generation failed: {str(e)}",
                details={"original_error": str(e)}
            )
    
    def generate_and_save(self, prompt: str, save_path: str, options: Optional[ImageOptions] = None) -> ImageResult:
        """
        Generate an image and save it to a file.
        
        📚 CONCEPT: Convenience Methods
        -------------------------------
        This is a "convenience method" that combines two common operations:
        1. Generate image
        2. Download and save it
        
        This saves users from having to call multiple methods, making the
        API easier to use for common scenarios.
        
        Args:
            prompt: Text description of the desired image
            save_path: Where to save the image file
            options: Optional generation configuration
            
        Returns:
            ImageResult with image saved to file
            
        Raises:
            ValueError: If prompt or save_path is invalid
            ImageError: If generation or saving fails
        """
        # Generate the image first
        result = self.generate_image(prompt, options)
        
        # Download and save
        result = self.download_and_save_image(result, save_path)
        
        return result
    
    def download_and_save_image(self, result: ImageResult, save_path: str) -> ImageResult:
        """
        Download an image from URL and save to file.
        
        📚 CONCEPT: Side Effects and Immutability
        -----------------------------------------
        This method modifies the ImageResult object (adds file_path and image_data).
        In a more functional style, we'd return a new object. But for simplicity
        and performance, we modify the existing one.
        
        Args:
            result: ImageResult with image_url
            save_path: Where to save the image file
            
        Returns:
            Updated ImageResult with image saved to file
            
        Raises:
            ImageError: If download or save fails
        """
        if not result.image_url:
            raise ImageError(
                code="DOWNLOAD_ERROR",
                message="No image URL available for download",
                details={"result": str(result)}
            )
        
        try:
            # Download image data
            response = requests.get(result.image_url, timeout=30)
            response.raise_for_status()
            
            # Update result with image data
            result.image_data = response.content
            
            # Save to file
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(result.image_data)
            
            # Update result with file path
            result.file_path = save_path
            
            return result
            
        except requests.RequestException as e:
            raise ImageError(
                code="DOWNLOAD_ERROR",
                message=f"Failed to download image: {str(e)}",
                details={"url": result.image_url, "error": str(e)}
            )
        except OSError as e:
            raise ImageError(
                code="SAVE_ERROR",
                message=f"Failed to save image: {str(e)}",
                details={"save_path": save_path, "error": str(e)}
            )
    
    def validate_prompt(self, prompt: str) -> bool:
        """
        Validate an image generation prompt.
        
        📚 CONCEPT: Business Rules Validation
        -------------------------------------
        Different from technical validation (in the client). This checks
        business rules:
        - Length limits (user experience)
        - Content appropriateness (basic checks)
        - Format requirements
        
        🎯 WHY VALIDATE HERE?
        ---------------------
        - Fail fast (before expensive API calls)
        - Better user experience (clear error messages)
        - Cost control (avoid wasted API credits)
        - Consistent rules (all entry points use same validation)
        
        Args:
            prompt: The prompt to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not prompt:
            return False
        
        # Check if prompt is just whitespace
        if not prompt.strip():
            return False
        
        # Check length (OpenAI limit is 4000 characters)
        if len(prompt) > 4000:
            return False
        
        # Basic content checks (extend as needed)
        prompt_lower = prompt.lower()
        
        # Check for potentially problematic content
        # (This is basic - real content filtering would be more sophisticated)
        problematic_terms = ['violence', 'gore', 'explicit']
        if any(term in prompt_lower for term in problematic_terms):
            return False
        
        return True
    
    def create_options_for_quality(self, quality: str = "standard") -> ImageOptions:
        """
        Create ImageOptions configured for a specific quality level.
        
        📚 CONCEPT: Factory Methods
        ---------------------------
        Instead of making users understand all the technical details of
        ImageOptions, we provide convenient factory methods for common scenarios.
        
        EXAMPLE USAGE:
        >>> # Instead of this complex setup:
        >>> options = ImageOptions(
        ...     model="dall-e-3",
        ...     size="1024x1024", 
        ...     quality="hd",
        ...     style="vivid"
        ... )
        >>> 
        >>> # Users can do this:
        >>> options = service.create_options_for_quality("high")
        
        Args:
            quality: Quality level ("standard", "high", "fast")
            
        Returns:
            ImageOptions configured for the requested quality
            
        Raises:
            ValueError: If quality level is unknown
        """
        if quality == "standard":
            return ImageOptions(
                model="dall-e-3",
                size="1024x1024",
                quality="standard",
                style="natural"
            )
        elif quality == "high":
            return ImageOptions(
                model="dall-e-3",
                size="1024x1024",
                quality="hd",
                style="vivid"
            )
        elif quality == "fast":
            return ImageOptions(
                model="dall-e-2",
                size="512x512"
            )
        else:
            raise ValueError(f"Unknown quality level: {quality}. Use 'standard', 'high', or 'fast'")
    
    def _generate_safe_filename(self, prompt: str, generation_id: str) -> str:
        """
        Generate a safe filename from a prompt and generation ID.
        
        📚 CONCEPT: Defensive Programming
        ---------------------------------
        User prompts can contain characters that aren't safe for filenames:
        - Spaces, special characters, unicode
        - Very long prompts
        - System-reserved names
        
        This method creates clean, filesystem-safe filenames.
        
        Args:
            prompt: The original image prompt
            generation_id: Unique identifier for this generation
            
        Returns:
            Safe filename with .png extension
            
        Example:
            prompt = "A cat wearing a space helmet!"
            generation_id = "gen-abc123"
            result = "a_cat_wearing_a_space_helmet_gen-abc123.png"
        """
        # Clean the prompt: lowercase, replace spaces and special chars with underscores
        clean_prompt = re.sub(r'[^\w\s-]', '', prompt.lower())
        clean_prompt = re.sub(r'[-\s]+', '_', clean_prompt)
        
        # Truncate if too long (keep it under 50 chars for readability)
        if len(clean_prompt) > 50:
            clean_prompt = clean_prompt[:50].rstrip('_')
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Combine: prompt + timestamp + generation_id
        filename = f"{clean_prompt}_{timestamp}_{generation_id}.png"
        
        return filename
