"""
📖 CHAPTER 3: THE TRANSLATOR - Image Generation Response Parser
================================================================

STORY: Making Sense of the API Response
----------------------------------------
In Chapter 2, our Client successfully talked to OpenAI and got back raw data.
But this data is in OpenAI's format - not ours! That's where the Parser comes in.

Think of it like a translator at the United Nations:
- Client speaks to OpenAI in "API language" (JSON, HTTP)
- OpenAI responds in "API language" (complex nested dictionaries)
- Parser translates into "our language" (clean domain models)
- Service layer gets nice, clean objects to work with

This separation is crucial because:
1. APIs change their response format
2. We might switch to a different AI provider someday
3. Our business logic shouldn't care about API details
4. Testing is easier with clean, predictable models

LEARNING OBJECTIVES:
-------------------
✓ Understand the role of parsers in clean architecture
✓ Learn defensive programming (handle unexpected API responses)
✓ See how to extract specific data from complex structures
✓ Master error handling and validation
✓ Appreciate separation of concerns (parsing vs business logic)
"""

import base64
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from src.models import ImageResult, ImageMetadata, ImageError


class ImageResponseParser:
    """
    Parser for OpenAI DALL-E image generation API responses.
    
    📚 CONCEPT: The Parser Pattern
    ------------------------------
    This class transforms raw API responses into our clean domain models.
    It's like a translator that converts between two languages:
    
    INPUT (OpenAI format):
    {
        "created": 1698700000,
        "data": [
            {
                "url": "https://oaidalleapi...",
                "revised_prompt": "A fluffy orange cat..."
            }
        ]
    }
    
    OUTPUT (Our format):
    ImageResult(
        prompt="A cat",
        image_url="https://oaidalleapi...",
        metadata=ImageMetadata(...),
        generation_id="gen-123"
    )
    
    📝 WHY SEPARATE PARSING?
    ------------------------
    1. API formats change → only parser needs updates
    2. Different providers → swap parsers, keep business logic
    3. Testing → mock clean objects, not complex API responses
    4. Maintainability → each class has one responsibility
    """
    
    def parse(self, response: Dict[str, Any], prompt: str) -> ImageResult:
        """
        Parse an OpenAI DALL-E API response into an ImageResult.
        
        📚 CONCEPT: Defensive Programming
        ---------------------------------
        We can't trust external APIs to always return perfect data.
        This method includes lots of validation and fallbacks:
        
        ✓ Check if response has expected structure
        ✓ Handle missing fields gracefully
        ✓ Provide sensible defaults
        ✓ Give clear error messages
        
        EXAMPLE INPUT:
        {
            "created": 1698700000,
            "data": [
                {
                    "url": "https://oaidalleapi.azureedge.net/...",
                    "revised_prompt": "A detailed illustration of a fluffy orange cat..."
                }
            ]
        }
        
        Args:
            response: Raw API response dictionary from OpenAI
            prompt: The original prompt from the user
            
        Returns:
            ImageResult object with parsed data
            
        Raises:
            ImageError: If response structure is invalid or missing required data
        """
        # Validate basic response structure
        if not isinstance(response, dict):
            raise ImageError(
                code="PARSING_ERROR",
                message="Response is not a valid dictionary",
                details={"response_type": type(response).__name__}
            )
        
        if "data" not in response:
            raise ImageError(
                code="PARSING_ERROR",
                message="No 'data' field in response",
                details={"response_keys": list(response.keys())}
            )
        
        data_list = response["data"]
        if not data_list:
            raise ImageError(
                code="PARSING_ERROR",
                message="No images in response data",
                details={"data_length": len(data_list)}
            )
        
        # Extract first image (DALL-E 3 only returns one)
        image_data = data_list[0]
        
        # Extract URL or base64 data
        image_url = image_data.get("url")
        b64_json = image_data.get("b64_json")
        
        if not image_url and not b64_json:
            raise ImageError(
                code="PARSING_ERROR",
                message="No image URL or base64 data in response",
                details={"image_data_keys": list(image_data.keys())}
            )
        
        # Create metadata
        metadata = ImageMetadata(
            prompt=prompt,
            revised_prompt=image_data.get("revised_prompt"),
            size="1024x1024",  # Default, could be extracted from options
            model="dall-e-3",   # Default, could be extracted from options
            created_at=self._parse_timestamp(response.get("created"))
        )
        
        # Generate unique ID for tracking
        generation_id = f"gen-{uuid.uuid4().hex[:8]}"
        
        # Create result
        result = ImageResult(
            prompt=prompt,
            image_url=image_url,
            metadata=metadata,
            generation_id=generation_id,
            timestamp=datetime.now()
        )
        
        # If we have base64 data, decode it
        if b64_json:
            try:
                result.image_data = base64.b64decode(b64_json)
            except Exception as e:
                raise ImageError(
                    code="PARSING_ERROR",
                    message="Failed to decode base64 image data",
                    details={"error": str(e)}
                )
        
        return result
    
    def _parse_timestamp(self, timestamp: Optional[Any]) -> datetime:
        """
        Parse timestamp from API response.
        
        📝 DEFENSIVE PROGRAMMING:
        OpenAI returns Unix timestamps (seconds since 1970).
        But what if they change the format? Or return None?
        This method handles all cases gracefully.
        
        Args:
            timestamp: Timestamp from API (usually int, but could be anything)
            
        Returns:
            datetime object
        """
        if timestamp is None:
            return datetime.now()
        
        try:
            # Try to convert to int (Unix timestamp)
            if isinstance(timestamp, str):
                timestamp = int(float(timestamp))
            elif isinstance(timestamp, float):
                timestamp = int(timestamp)
            
            # Convert Unix timestamp to datetime
            return datetime.fromtimestamp(timestamp)
            
        except (ValueError, TypeError, OSError):
            # Fallback to current time if parsing fails
            return datetime.now()
    
    def format_for_display(self, result: ImageResult) -> str:
        """
        Format an ImageResult for display to users.
        
        📚 CONCEPT: User Experience
        ---------------------------
        This creates a human-readable summary of the image generation.
        Different from __str__ because it's designed for end users,
        not developers.
        
        EXAMPLE OUTPUT:
        ================================================================================
        Image Generated Successfully
        ================================================================================
        
        Prompt: A space cat wearing an astronaut helmet
        Model: dall-e-3 (1024x1024)
        Generated: 2024-10-27 10:30:15
        
        Revised Prompt: A detailed illustration of a fluffy orange cat wearing a 
        white NASA astronaut helmet, floating in space with Earth visible in the 
        background, digital art style
        
        Image URL: https://oaidalleapi.azureedge.net/...
        Status: ✓ Ready for download
        ================================================================================
        
        Args:
            result: ImageResult to format
            
        Returns:
            Formatted string for display
        """
        lines = []
        lines.append("=" * 80)
        lines.append("Image Generated Successfully")
        lines.append("=" * 80)
        lines.append("")
        
        # Basic info
        lines.append(f"Prompt: {result.prompt}")
        if result.metadata:
            model_info = f"{result.metadata.model}"
            if result.metadata.size:
                model_info += f" ({result.metadata.size})"
            lines.append(f"Model: {model_info}")
            lines.append(f"Generated: {result.metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        lines.append("")
        
        # Revised prompt (if available)
        if result.metadata and result.metadata.revised_prompt:
            lines.append("Revised Prompt:")
            # Wrap long text
            revised = result.metadata.revised_prompt
            words = revised.split()
            current_line = ""
            for word in words:
                if len(current_line + word + " ") <= 76:
                    current_line += word + " "
                else:
                    lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())
            lines.append("")
        
        # Image location
        if result.image_url:
            lines.append(f"Image URL: {result.image_url}")
        
        # Status
        status_parts = []
        if result.is_downloaded:
            status_parts.append("✓ Downloaded")
        else:
            status_parts.append("⏳ Ready for download")
        
        if result.is_saved:
            status_parts.append(f"✓ Saved to {result.file_path}")
        
        lines.append(f"Status: {' | '.join(status_parts)}")
        
        # Generation ID for reference
        lines.append(f"ID: {result.generation_id}")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
