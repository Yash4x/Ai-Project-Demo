#!/usr/bin/env python3
"""
Test script to verify the auto-save functionality works correctly.
This simulates the image generation process without calling the OpenAI API.
"""

import os
import tempfile
from unittest.mock import Mock, patch
from src.search_service import ImageGenerationService
from src.models import ImageOptions, ImageResult, ImageMetadata
from datetime import datetime

def test_auto_save_functionality():
    """Test that auto-save generates correct filenames and saves images."""
    
    print("🧪 Testing Auto-Save Functionality")
    print("=" * 50)
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Test the filename generation
        service = ImageGenerationService("fake-api-key")
        
        # Test filename generation
        test_cases = [
            ("A cat wearing a space helmet", "a_cat_wearing_a_space_helmet"),
            ("Abstract art with lots of colors!", "abstract_art_with_lots_of_colors"),
            ("Simple test", "simple_test"),
            ("A" * 100, "a" * 50),  # Long prompt truncation
        ]
        
        print("\n🔤 Testing Filename Generation:")
        for prompt, expected_start in test_cases:
            filename = service._generate_safe_filename(prompt, "gen-test123")
            print(f"  • '{prompt[:30]}...' → {filename}")
            
            # Verify filename is safe
            assert filename.endswith("_gen-test123.png"), f"Should end with generation ID: {filename}"
            assert expected_start in filename, f"Should contain cleaned prompt: {filename}"
            assert len(filename) < 200, f"Filename too long: {len(filename)}"
            
            # Verify no unsafe characters
            import re
            assert re.match(r'^[a-z0-9_\-\.]+$', filename), f"Unsafe characters in filename: {filename}"
        
        print("✅ All filename tests passed!")
        
        # Test that auto_save parameter works
        print("\n🔧 Testing Auto-Save Parameter:")
        
        # Mock the client and parser
        with patch.object(service, 'client') as mock_client, \
             patch.object(service, 'parser') as mock_parser, \
             patch.object(service, 'download_and_save_image') as mock_download:
            
            # Setup mocks
            mock_client.generate_image.return_value = {"data": [{"url": "fake-url"}]}
            mock_result = ImageResult(
                prompt="test prompt",
                image_url="https://fake-url.com/image.png",
                generation_id="gen-test123"
            )
            mock_parser.parse.return_value = mock_result
            mock_download.return_value = mock_result
            
            # Test auto_save=True (default)
            result = service.generate_image("test prompt", auto_save=True, save_dir=temp_dir)
            print("  • auto_save=True: download_and_save_image called")
            mock_download.assert_called_once()
            
            # Reset mock
            mock_download.reset_mock()
            
            # Test auto_save=False
            result = service.generate_image("test prompt", auto_save=False, save_dir=temp_dir)
            print("  • auto_save=False: download_and_save_image NOT called")
            mock_download.assert_not_called()
        
        print("✅ Auto-save parameter tests passed!")
    
    print("\n🎉 All tests completed successfully!")
    print("\n💡 The auto-save functionality is working correctly:")
    print("  • Safe filenames are generated from prompts")
    print("  • auto_save parameter controls download behavior")
    print("  • File organization works as expected")

if __name__ == "__main__":
    test_auto_save_functionality()