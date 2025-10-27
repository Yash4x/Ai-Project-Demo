"""
📖 CHAPTER 1: THE FOUNDATION - DATA MODELS
==========================================

STORY: Building Blocks of Our Image Generation Application
----------------------------------------------------------
Imagine you're building a house. Before you start construction, you need blueprints.
In software, these blueprints are called "data models" - they define the shape and
structure of the information flowing through your application.

This is where our story begins. We'll create essential blueprints for image generation:
1. ImageOptions - Configuration for image generation (the request)
2. ImageMetadata - Information about the generated image (the details)
3. ImageResult - The complete result with image data (the response)
4. ImageError - When things go wrong (the exception handling)

LEARNING OBJECTIVES:
-------------------
✓ Understand Python dataclasses (automatic constructors & repr)
✓ Learn type hints for better code documentation
✓ Master properties (computed attributes)
✓ See how custom exceptions work
✓ Appreciate immutability and data validation
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Union


# ============================================================================
# BLUEPRINT 1: ImageOptions - Configuring Image Generation
# ============================================================================

@dataclass
class ImageOptions:
    """
    Configuration options for image generation requests.
    
    📚 CONCEPT: Dataclasses
    -----------------------
    The @dataclass decorator is Python's way of saying "this is just data."
    It automatically generates __init__, __repr__, and __eq__ methods.
    
    Think of it like filling out a form for an art commission:
    - model: Which AI model to use for generation (dall-e-3, dall-e-2)
    - size: Image dimensions (1024x1024, 1792x1024, etc.)
    - quality: Image quality level (standard, hd)
    - style: Art style (vivid, natural)
    - response_format: How to return image (url, b64_json)
    
    📝 DESIGN DECISION: Default Values
    ----------------------------------
    Notice the = signs? These are default values. If you don't specify a model,
    it defaults to "dall-e-3" (the highest quality option).
    
    EXAMPLE USAGE:
    >>> # Use all defaults
    >>> options = ImageOptions()
    >>> 
    >>> # Customize for your needs
    >>> options = ImageOptions(
    ...     model="dall-e-2",
    ...     size="512x512",
    ...     quality="standard"
    ... )
    """
    
    # Which AI model to use for image generation
    model: str = "dall-e-3"
    
    # Image size (dall-e-3: 1024x1024, 1792x1024, 1024x1792; dall-e-2: 256x256, 512x512, 1024x1024)
    size: str = "1024x1024"
    
    # Image quality (dall-e-3 only: "standard" or "hd")
    quality: str = "standard"
    
    # Style (dall-e-3 only: "vivid" or "natural")
    style: str = "vivid"
    
    # Response format ("url" or "b64_json")
    response_format: str = "url"
    
    # Number of images to generate (1-10 for dall-e-2, only 1 for dall-e-3)
    n: int = 1


# ============================================================================
# BLUEPRINT 2: ImageMetadata - Information About Generated Images
# ============================================================================

@dataclass
class ImageMetadata:
    """
    Metadata about a generated image.
    
    📚 CONCEPT: Image Metadata
    --------------------------
    Just like photos from your camera contain EXIF data (when taken, camera settings),
    our generated images have metadata about how they were created.
    
    Think of this like a recipe card for a dish:
    - prompt: What you asked for (the recipe name)
    - revised_prompt: What the AI actually made (chef's interpretation)
    - size: Image dimensions (serving size)
    - model: Which AI created it (which chef)
    - created_at: When it was generated (when cooked)
    
    📝 DESIGN DECISION: Optional Fields
    -----------------------------------
    Some fields are Optional because different models return different data:
    - DALL-E 3 provides revised_prompt (improved version of your prompt)
    - DALL-E 2 doesn't revise prompts, so revised_prompt might be None
    
    EXAMPLE USAGE:
    >>> metadata = ImageMetadata(
    ...     prompt="A cat wearing a astronaut helmet",
    ...     revised_prompt="A fluffy orange cat wearing a white NASA astronaut helmet...",
    ...     size="1024x1024",
    ...     model="dall-e-3",
    ...     created_at=datetime.now()
    ... )
    >>> print(metadata.is_high_resolution)  # True
    """
    
    # The original prompt provided by the user
    prompt: str
    
    # The revised prompt (DALL-E 3 may enhance your prompt for better results)
    revised_prompt: Optional[str] = None
    
    # Image dimensions (e.g., "1024x1024", "1792x1024")
    size: str = "1024x1024"
    
    # Model used for generation
    model: str = "dall-e-3"
    
    # Quality setting used (if applicable)
    quality: Optional[str] = None
    
    # Style setting used (if applicable)
    style: Optional[str] = None
    
    # When the image was generated
    created_at: datetime = None
    
    def __post_init__(self):
        """Set created_at to current time if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def is_high_resolution(self) -> bool:
        """
        Check if this is a high-resolution image.
        
        � PRACTICAL USE:
        High-res images are better for:
        - Printing
        - Professional use
        - Detail work
        
        But they also:
        - Cost more to generate
        - Take longer to load
        - Use more storage
        """
        width, height = map(int, self.size.split('x'))
        return width >= 1024 and height >= 1024
    
    @property
    def aspect_ratio(self) -> str:
        """
        Get the aspect ratio as a simplified fraction.
        
        📝 EXAMPLE RATIOS:
        - 1024x1024 → "1:1" (square)
        - 1792x1024 → "16:9" (widescreen)
        - 1024x1792 → "9:16" (portrait)
        """
        width, height = map(int, self.size.split('x'))
        
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a
        
        divisor = gcd(width, height)
        return f"{width//divisor}:{height//divisor}"
    
    def __str__(self) -> str:
        """Format metadata for display."""
        return f"{self.model} {self.size} - {self.prompt[:50]}..."


# ============================================================================
# BLUEPRINT 3: ImageResult - The Complete Generated Image Package
# ============================================================================

@dataclass
class ImageResult:
    """
    Represents the complete result of an image generation operation.
    
    📚 CONCEPT: Aggregation - Combining Multiple Data Types
    --------------------------------------------------------
    This is where everything comes together! An ImageResult is like a gift box
    that contains multiple items:
    - The image data (what you asked for)
    - Metadata (information about the generation)
    - File information (for saving/loading)
    
    🎯 REAL-WORLD ANALOGY:
    ----------------------
    Imagine commissioning an artist to paint something. They return:
    - prompt: Your original request (so you remember what you asked)
    - image_url: Where to view the finished artwork
    - image_data: The actual image bytes (if downloaded)
    - metadata: Details about how it was created
    - file_path: Where it's saved on your computer
    - generation_id: Commission number (for tracking)
    
    📝 DESIGN: Why Optional Fields?
    -------------------------------
    Different scenarios need different data:
    - Online viewing: Only need image_url
    - Offline storage: Need image_data and file_path
    - API integration: Need generation_id for tracking
    
    EXAMPLE USAGE:
    >>> result = ImageResult(
    ...     prompt="A space cat",
    ...     image_url="https://oaidalleapi...",
    ...     metadata=ImageMetadata(...),
    ...     generation_id="gen-123"
    ... )
    >>> 
    >>> # Check if image is saved locally
    >>> if result.is_downloaded:
    ...     print(f"Image saved to: {result.file_path}")
    """
    
    # The original prompt from the user
    prompt: str
    
    # URL to the generated image (from OpenAI)
    image_url: Optional[str] = None
    
    # Binary image data (when downloaded)
    image_data: Optional[bytes] = None
    
    # Metadata about the image generation
    metadata: Optional[ImageMetadata] = None
    
    # Local file path (when saved to disk)
    file_path: Optional[str] = None
    
    # Unique identifier for this generation (for logging/debugging)
    generation_id: str = ""
    
    # When this generation was completed
    timestamp: datetime = None
    
    def __post_init__(self):
        """Set timestamp to current time if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def is_downloaded(self) -> bool:
        """
        Check if the image has been downloaded.
        
        💡 WHY CHECK THIS?
        ------------------
        URLs from OpenAI expire after a few hours, so you might want to:
        - Download immediately for long-term storage
        - Check if download is needed before displaying
        - Warn users about expiring links
        """
        return self.image_data is not None
    
    @property
    def is_saved(self) -> bool:
        """Check if the image has been saved to a file."""
        return self.file_path is not None
    
    @property
    def file_size(self) -> Optional[int]:
        """Get the size of the image data in bytes."""
        return len(self.image_data) if self.image_data else None
    
    def __str__(self) -> str:
        """
        Concise string representation for logging.
        
        📝 DESIGN: Why Not Print Everything?
        ------------------------------------
        We only show prompt and basic status because:
        - Logs should be scannable (not walls of text)
        - You can always access full data via attributes
        - This appears in error messages and debug logs
        """
        status = []
        if self.is_downloaded:
            status.append("downloaded")
        if self.is_saved:
            status.append("saved")
        status_str = f" ({', '.join(status)})" if status else ""
        return f"ImageResult(prompt='{self.prompt[:30]}...'{status_str})"


# ============================================================================
# BLUEPRINT 4: ImageError - When Things Go Wrong
# ============================================================================

@dataclass
class ImageError(Exception):
    """
    Custom exception for image generation-related errors.
    
    📚 CONCEPT: Exception Hierarchies
    ---------------------------------
    Python has built-in exceptions (ValueError, TypeError, etc.) but sometimes
    you need your own. By inheriting from Exception, we create a custom error
    type that can carry more information than a simple error message.
    
    🎯 WHY CUSTOM EXCEPTIONS?
    --------------------------
    Compare these two approaches:
    
    ❌ BAD: Generic exception
    raise Exception("Something went wrong with code 401")
    - Hard to catch specific errors
    - No structured data
    - Can't handle different errors differently
    
    ✅ GOOD: Custom exception
    raise ImageError(code="AUTHENTICATION_ERROR", message="Invalid API key")
    - Can catch ImageError specifically
    - Machine-readable error codes
    - Can include debug details
    
    📝 ERROR CODES WE USE:
    ----------------------
    - AUTHENTICATION_ERROR: Invalid API key
    - RATE_LIMIT_ERROR: Too many requests
    - API_ERROR: OpenAI service problems
    - VALIDATION_ERROR: Invalid input data (bad prompt, size, etc.)
    - CONTENT_POLICY_ERROR: Prompt violates OpenAI's usage policies
    - GENERATION_ERROR: Image generation failed
    - DOWNLOAD_ERROR: Failed to download generated image
    - SAVE_ERROR: Failed to save image to file
    - UNKNOWN_ERROR: Unexpected issues
    
    EXAMPLE USAGE:
    >>> # Raising an error with context
    >>> if not api_key:
    ...     raise ImageError(
    ...         code="AUTHENTICATION_ERROR",
    ...         message="API key is required",
    ...         details={"hint": "Set OPENAI_API_KEY environment variable"}
    ...     )
    >>> 
    >>> # Catching and handling
    >>> try:
    ...     result = generate_image("A space cat")
    ... except ImageError as e:
    ...     if e.code == "RATE_LIMIT_ERROR":
    ...         print("Slow down! Try again in 60 seconds")
    ...     elif e.code == "CONTENT_POLICY_ERROR":
    ...         print("Try a different prompt - this one violates content policy")
    ...     else:
    ...         print(f"Error: {e}")
    """
    
    # Machine-readable error code (for programmatic handling)
    code: str
    
    # Human-readable error message (for display to users)
    message: str
    
    # Optional extra information for debugging (logs, stack traces, etc.)
    details: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        """
        Format error for display.
        
        PATTERN: Structured Error Messages
        ----------------------------------
        Format: [CODE] Message
        Example: [CONTENT_POLICY_ERROR] Prompt violates usage policies
        
        This makes logs searchable:
        grep "CONTENT_POLICY_ERROR" logs.txt
        """
        error_str = f"[{self.code}] {self.message}"
        if self.details:
            error_str += f" | Details: {self.details}"
        return error_str


# ============================================================================
# BLUEPRINT 5: Story Generation Models
# ============================================================================

@dataclass
class StoryOptions:
    """
    Configuration options for story-based image generation.
    
    CONCEPT: Story Generation
    -------------------------
    Instead of generating a single image, we break down a story prompt
    into multiple scenes and generate an image for each scene.
    
    Example: "A cat going to shop for watermelons"
    Becomes 5 scenes:
    1. Cat waking up and deciding to go shopping
    2. Cat walking to the market
    3. Cat examining watermelons at the fruit stand
    4. Cat selecting and purchasing a watermelon
    5. Cat walking home happily with the watermelon
    """
    # Story configuration
    story_prompt: str
    num_scenes: int = 5
    
    # Image generation options for each scene
    model: str = "dall-e-3"
    size: str = "1024x1024" 
    quality: str = "standard"
    style: str = "vivid"
    
    # Auto-save options
    auto_save: bool = True
    save_path: Optional[str] = None


@dataclass
class StoryScene:
    """
    Individual scene in a visual story.
    
    CONCEPT: Scene Decomposition
    ----------------------------
    Each scene represents one moment in the story timeline.
    Contains both the narrative description and visual prompt.
    """
    scene_number: int
    narrative: str  # Brief description of what happens
    image_prompt: str  # Detailed prompt for image generation
    image_result: Optional[ImageResult] = None
    
    @property
    def is_generated(self) -> bool:
        """Check if this scene has been generated."""
        return self.image_result is not None


@dataclass  
class StoryResult:
    """
    Container for story generation results.
    
    CONCEPT: Aggregated Results
    ---------------------------
    Combines all scenes into a cohesive story result.
    Provides convenient methods for accessing story data.
    """
    story_prompt: str
    scenes: List[StoryScene]
    generation_time: datetime
    total_generation_time: float = 0.0
    
    @property
    def num_scenes(self) -> int:
        """Number of scenes in the story."""
        return len(self.scenes)
    
    @property
    def completed_scenes(self) -> List[StoryScene]:
        """List of successfully generated scenes."""
        return [scene for scene in self.scenes if scene.is_generated]
    
    @property
    def failed_scenes(self) -> List[StoryScene]:
        """List of scenes that failed to generate."""
        return [scene for scene in self.scenes if not scene.is_generated]
    
    @property
    def success_rate(self) -> float:
        """Percentage of successfully generated scenes."""
        if not self.scenes:
            return 0.0
        return (len(self.completed_scenes) / len(self.scenes)) * 100
    
    @property
    def all_image_urls(self) -> List[str]:
        """Get all generated image URLs."""
        urls = []
        for scene in self.completed_scenes:
            if scene.image_result and scene.image_result.image_url:
                urls.append(scene.image_result.image_url)
        return urls
    
    def get_scene_filenames(self) -> List[str]:
        """Get saved filenames for all scenes."""
        filenames = []
        for scene in self.completed_scenes:
            if scene.image_result and scene.image_result.file_path:
                filenames.append(scene.image_result.file_path)
        return filenames
