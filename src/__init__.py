"""
AI Image Generation Demo - A demonstration of OpenAI's DALL-E image generation capabilities.

This package provides a CLI tool for generating images using OpenAI's DALL-E API.
"""

__version__ = "1.0.0"
__author__ = "Enterprise Development Team"

from src.models import ImageOptions, ImageResult, ImageMetadata, ImageError
from src.client import ImageGenerationClient
from src.parser import ImageResponseParser
from src.search_service import ImageGenerationService

__all__ = [
    "ImageOptions",
    "ImageResult", 
    "ImageMetadata",
    "ImageError",
    "ImageGenerationClient",
    "ImageResponseParser",
    "ImageGenerationService",
]
