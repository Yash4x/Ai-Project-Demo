"""
📖 CHAPTER 2: THE MESSENGER - OpenAI Image Generation Client
=============================================================

STORY: Talking to the AI for Image Generation
----------------------------------------------
In Chapter 1, we created blueprints (data models). Now we need someone to actually
TALK to OpenAI's DALL-E servers. That's what this Client does - it's like a messenger who:

1. Takes our request (an image prompt)
2. Packages it in the format OpenAI expects (JSON payload)
3. Sends it over the internet (HTTP POST)
4. Waits for the response
5. Brings back the image data

Think of it like commissioning an artist:
- You (main.py) → tell the messenger what artwork you want
- Messenger (client.py) → calls the artist (OpenAI DALL-E API)
- Artist → creates the image (runs AI model)
- Messenger → brings back your artwork (API response with image URL)

LEARNING OBJECTIVES:
-------------------
✓ Understand API clients and HTTP requests
✓ Learn environment variable management (.env files)
✓ Master error handling and retries
✓ See defensive programming (validate inputs)
✓ Appreciate separation of concerns (Client = communication ONLY)
"""

import os
from typing import Optional, Dict, Any, List

# OpenAI's official Python library - handles HTTPS, auth, retries
from openai import OpenAI, AuthenticationError, RateLimitError, APIError

# Load environment variables from .env file (keeps secrets out of code)
from dotenv import load_dotenv

# Our data models from Chapter 1
from src.models import ImageOptions, ImageError, StoryOptions, StoryScene


# ============================================================================
# INITIALIZATION: Load secrets before any class code runs
# ============================================================================
# 📝 CONCEPT: Why load_dotenv() here?
# ------------------------------------
# This runs when the module is IMPORTED (before any functions are called).
# It loads variables from .env file into os.environ, so this code:
#   api_key = os.getenv("OPENAI_API_KEY")
# ...can find the key without us having to remember to load it.
#
# 💡 SECURITY: Why use .env files?
# --------------------------------
# ❌ NEVER: api_key = "sk-abc123..."  # Hardcoded in source code
# ✅ ALWAYS: api_key = os.getenv("OPENAI_API_KEY")  # From environment
#
# If you commit hardcoded keys to git, they're public forever (even if deleted).
load_dotenv()


# ============================================================================
# THE CLIENT CLASS: Our Messenger to OpenAI
# ============================================================================

class ImageGenerationClient:
    """
    Client for interacting with OpenAI's DALL-E image generation API.
    
    📚 CONCEPT: The Client Pattern
    -------------------------------
    A "client" in software is code that talks to a server/service. Think of it
    like commissioning an artist:
    - You → tell the agent what artwork you want (user code)
    - Agent → tells the artist (client)
    - Artist → creates the artwork (OpenAI's DALL-E servers)
    - Agent → brings artwork back (client returns response)
    
    This class ONLY handles communication. It doesn't:
    - ❌ Validate business logic (that's the service layer)
    - ❌ Parse responses (that's the parser)
    - ❌ Present to users (that's the main app)
    
    It DOES:
    - ✓ Manage authentication
    - ✓ Build HTTP requests  
    - ✓ Handle network errors
    - ✓ Translate API errors into our domain errors
    
    📝 DESIGN DECISION: Why a Class?
    ---------------------------------
    We could have used functions:
    
    def generate_image(api_key: str, prompt: str) -> dict:
        ...
    
    But a class is better because:
    1. State management (api_key stored once, not passed everywhere)
    2. Multiple related methods (generate, validate, construct_payload)
    3. Easy to mock in tests
    4. Follows industry patterns (easier for others to understand)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the image generation client.
        
        📚 CONCEPT: Dependency Injection
        --------------------------------
        This pattern is called "dependency injection." You can provide the API
        key explicitly OR let it load from environment. This makes code:
        - Flexible: Works in multiple environments (dev, test, prod)
        - Testable: Can inject a fake key in tests
        - Secure: Doesn't require hardcoded secrets
        
        EXAMPLE USAGE:
        >>> # Option 1: Explicit key (for testing)
        >>> client = ImageGenerationClient(api_key="sk-test-123")
        >>> 
        >>> # Option 2: From environment (for production)
        >>> # Assumes .env has OPENAI_API_KEY=sk-abc...
        >>> client = ImageGenerationClient()
        
        💡 PATTERN: The "or" Operator
        ------------------------------
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        How this works:
        - If api_key is provided and truthy → use it
        - If api_key is None or empty → check os.getenv()
        - If both fail → self.api_key = None (caught below)
        
        Args:
            api_key: OpenAI API key. If None, will load from OPENAI_API_KEY
                    environment variable.
            
        Raises:
            ValueError: If no API key is provided or found
        """
        # Try explicit key first, fall back to environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # Fail fast if no key available
        # 📝 PATTERN: Fail Fast
        # Rather than waiting until we make a request (wasting time), we check
        # immediately. This gives users a clear error message at startup.
        if not self.api_key:
            raise ValueError(
                "API key must be provided or set in "
                "OPENAI_API_KEY environment variable"
            )
        
        # Create the official OpenAI client
        # This handles HTTPS, retries, timeouts automatically
        self.client = OpenAI(api_key=self.api_key)
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is in the correct format.
        
        📚 CONCEPT: Client-Side Validation
        -----------------------------------
        We check the key FORMAT before making API calls. This catches:
        - Typos in .env file (forgot "sk-" prefix)
        - Truncated keys (copy-paste errors)
        - Wrong type of keys (using project ID instead)
        
        Why not just try to use it?
        - API calls cost money (even failed ones may count)
        - Better error messages (tell user WHAT is wrong)
        - Faster feedback (no network roundtrip)
        
        💡 OpenAI Key Format:
        ---------------------
        All OpenAI API keys:
        - Start with "sk-" (secret key)
        - Are around 48-50 characters long
        - Contain alphanumeric characters
        
        EXAMPLE USAGE:
        >>> client = ImageGenerationClient(api_key="invalid")
        >>> if not client.validate_api_key():
        ...     print("Key looks wrong - check your .env file!")
        
        Returns:
            True if key appears valid, False otherwise
            
        ⚠️ NOTE: This only checks FORMAT, not if the key actually works.
                 A well-formatted key might still be expired/revoked.
        """
        return self.api_key.startswith("sk-") and len(self.api_key) > 20
    
    def generate_image(self, prompt: str, options: Optional[ImageOptions] = None) -> Dict[str, Any]:
        """
        Generate an image using OpenAI's DALL-E API.
        
        Args:
            prompt: The text prompt describing the desired image
            options: Optional image generation configuration
            
        Returns:
            Raw API response dictionary
            
        Raises:
            ValueError: If prompt is invalid
            ImageError: If API request fails
        """
        # Validate prompt
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        if len(prompt) > 4000:
            raise ValueError("Prompt too long (max 4000 characters)")
        
        # Use default options if none provided
        if options is None:
            options = ImageOptions()
        
        # Construct request payload
        payload = self._construct_payload(prompt, options)
        
        try:
            # Make API request
            response = self.client.images.generate(**payload)
            
            # Convert response to dictionary
            return self._response_to_dict(response)
            
        except AuthenticationError as e:
            raise ImageError(
                code="AUTHENTICATION_ERROR",
                message="Invalid API key or authentication failed",
                details={"original_error": str(e)}
            )
        except RateLimitError as e:
            raise ImageError(
                code="RATE_LIMIT_ERROR", 
                message="API rate limit exceeded",
                details={"original_error": str(e)}
            )
        except APIError as e:
            # Check if it's a content policy violation
            error_msg = str(e).lower()
            if "content policy" in error_msg or "safety" in error_msg:
                raise ImageError(
                    code="CONTENT_POLICY_ERROR",
                    message="Prompt violates OpenAI's content policy",
                    details={"original_error": str(e)}
                )
            else:
                raise ImageError(
                    code="API_ERROR",
                    message=f"API request failed: {str(e)}",
                    details={"original_error": str(e)}
                )
        except Exception as e:  # pragma: no cover
            # Defensive fallback - should not be reached in normal operation
            raise ImageError(
                code="UNKNOWN_ERROR",
                message=f"Unexpected error: {str(e)}",
                details={"original_error": str(e)}
            )
    
    def _construct_payload(self, prompt: str, options: ImageOptions) -> Dict[str, Any]:
        """
        Construct the API request payload.
        
        Args:
            prompt: The image generation prompt
            options: Image generation options
            
        Returns:
            Dictionary payload for API request
        """
        payload = {
            "model": options.model,
            "prompt": prompt,
            "size": options.size,
            "response_format": options.response_format,
            "n": options.n
        }
        
        # Add quality setting for DALL-E 3
        if options.model == "dall-e-3" and options.quality:
            payload["quality"] = options.quality
        
        # Add style setting for DALL-E 3
        if options.model == "dall-e-3" and options.style:
            payload["style"] = options.style
        
        return payload
    
    def _response_to_dict(self, response: Any) -> Dict[str, Any]:
        """
        Convert OpenAI response object to dictionary.
        
        Args:
            response: OpenAI image generation response object
            
        Returns:
            Dictionary representation of response
        """
        result = {
            "created": getattr(response, 'created', 0),
            "data": []
        }
        
        # Convert image data
        for image in response.data:
            image_dict = {}
            
            if hasattr(image, 'url'):
                image_dict["url"] = image.url
            
            if hasattr(image, 'b64_json'):
                image_dict["b64_json"] = image.b64_json
            
            if hasattr(image, 'revised_prompt'):
                image_dict["revised_prompt"] = image.revised_prompt
            
            result["data"].append(image_dict)
        
        return result

    def decompose_story(self, story_options: StoryOptions) -> List[StoryScene]:
        """
        Decompose a story prompt into individual scenes using GPT.
        
        This method uses GPT to break down a story into sequential scenes,
        each with a narrative description and detailed image prompt.
        
        Args:
            story_options: Configuration for story generation
            
        Returns:
            List of StoryScene objects, one for each scene
            
        Raises:
            ImageError: If story decomposition fails
        """
        try:
            # Create a detailed prompt for GPT to decompose the story
            system_prompt = f"""You are a creative storyteller and visual artist. Your task is to break down a story prompt into exactly {story_options.num_scenes} sequential scenes for image generation.

For each scene, provide:
1. A brief narrative description (1-2 sentences) of what happens
2. A detailed, visual prompt for image generation (3-4 sentences) that describes the scene in rich visual detail

Focus on:
- Clear progression from scene to scene
- Rich visual descriptions suitable for AI image generation
- Consistent characters and setting throughout
- Cinematic composition and lighting details

Output format: Return a JSON array with {story_options.num_scenes} objects, each containing "narrative" and "image_prompt" fields."""

            user_prompt = f"Story to break down: {story_options.story_prompt}"

            # Call GPT to decompose the story
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using the efficient model for text generation
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000
            )

            # Parse the JSON response
            import json
            story_data = json.loads(response.choices[0].message.content)
            
            # Convert to StoryScene objects
            scenes = []
            if isinstance(story_data, dict) and "scenes" in story_data:
                scene_list = story_data["scenes"]
            elif isinstance(story_data, list):
                scene_list = story_data
            else:
                raise ImageError(
                    "STORY_PARSING_ERROR",
                    "Unexpected response format from GPT"
                )

            for i, scene_data in enumerate(scene_list[:story_options.num_scenes]):
                scene = StoryScene(
                    scene_number=i + 1,
                    narrative=scene_data.get("narrative", f"Scene {i + 1}"),
                    image_prompt=scene_data.get("image_prompt", scene_data.get("narrative", f"Scene {i + 1}"))
                )
                scenes.append(scene)

            # Ensure we have the right number of scenes
            while len(scenes) < story_options.num_scenes:
                scenes.append(StoryScene(
                    scene_number=len(scenes) + 1,
                    narrative=f"Additional scene {len(scenes) + 1}",
                    image_prompt=f"Continue the story of {story_options.story_prompt}, scene {len(scenes) + 1}"
                ))

            return scenes

        except json.JSONDecodeError as e:
            raise ImageError(
                "STORY_PARSING_ERROR",
                f"Failed to parse GPT response as JSON: {str(e)}"
            )
        except Exception as e:
            if isinstance(e, ImageError):
                raise
            raise ImageError(
                "STORY_DECOMPOSITION_ERROR",
                f"Failed to decompose story: {str(e)}"
            )
