"""
Test module for story generation functionality.

This module tests the story generation features including:
- Story decomposition using GPT
- Multi-scene image generation
- Story result aggregation
- Error handling for story mode

The tests use pytest fixtures and mocking to avoid making real API calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.models import StoryOptions, StoryScene, StoryResult, ImageResult, ImageMetadata, ImageError
from src.search_service import ImageGenerationService
from src.client import ImageGenerationClient


class TestStoryModels:
    """Test the story-related data models."""
    
    def test_story_options_creation(self):
        """Test StoryOptions can be created with default values."""
        options = StoryOptions(story_prompt="A cat adventure")
        
        assert options.story_prompt == "A cat adventure"
        assert options.num_scenes == 5
        assert options.model == "dall-e-3"
        assert options.auto_save is True
    
    def test_story_scene_creation(self):
        """Test StoryScene can be created and tracks generation status."""
        scene = StoryScene(
            scene_number=1,
            narrative="Cat wakes up",
            image_prompt="A sleepy cat yawning in a sunny room"
        )
        
        assert scene.scene_number == 1
        assert scene.narrative == "Cat wakes up"
        assert scene.is_generated is False
        
        # Add a mock image result
        scene.image_result = Mock(spec=ImageResult)
        assert scene.is_generated is True
    
    def test_story_result_aggregation(self):
        """Test StoryResult properly aggregates scene data."""
        # Create test scenes
        successful_scene = StoryScene(
            scene_number=1,
            narrative="Success",
            image_prompt="Success prompt",
            image_result=Mock(spec=ImageResult)
        )
        
        failed_scene = StoryScene(
            scene_number=2,
            narrative="Failed",
            image_prompt="Failed prompt"
        )
        
        story_result = StoryResult(
            story_prompt="Test story",
            scenes=[successful_scene, failed_scene],
            generation_time=datetime.now()
        )
        
        assert story_result.num_scenes == 2
        assert len(story_result.completed_scenes) == 1
        assert len(story_result.failed_scenes) == 1
        assert story_result.success_rate == 50.0
    
    def test_story_result_filename_extraction(self):
        """Test that story results can extract saved filenames."""
        # Create mock image result with file path
        mock_result = Mock(spec=ImageResult)
        mock_result.file_path = "/path/to/scene1.png"
        
        scene = StoryScene(
            scene_number=1,
            narrative="Test",
            image_prompt="Test prompt",
            image_result=mock_result
        )
        
        story_result = StoryResult(
            story_prompt="Test",
            scenes=[scene],
            generation_time=datetime.now()
        )
        
        filenames = story_result.get_scene_filenames()
        assert filenames == ["/path/to/scene1.png"]


class TestStoryDecomposition:
    """Test GPT-based story decomposition."""
    
    @patch('src.client.ImageGenerationClient')
    def test_story_decomposition_success(self, mock_client_class):
        """Test successful story decomposition using GPT."""
        # Setup mock client
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        # Mock GPT response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''[
            {
                "narrative": "Cat wakes up and decides to go shopping",
                "image_prompt": "A sleepy orange cat stretching in a sunny bedroom"
            },
            {
                "narrative": "Cat walks to the market",
                "image_prompt": "An orange cat walking down a cobblestone street"
            }
        ]'''
        
        mock_client_instance.client.chat.completions.create.return_value = mock_response
        
        # Create client and test decomposition
        client = ImageGenerationClient("test-key")
        client.client = mock_client_instance.client
        
        story_options = StoryOptions(
            story_prompt="A cat going shopping",
            num_scenes=2
        )
        
        scenes = client.decompose_story(story_options)
        
        assert len(scenes) == 2
        assert scenes[0].scene_number == 1
        assert scenes[0].narrative == "Cat wakes up and decides to go shopping"
        assert "orange cat stretching" in scenes[0].image_prompt
        
        assert scenes[1].scene_number == 2
        assert scenes[1].narrative == "Cat walks to the market"
    
    @patch('src.client.ImageGenerationClient')
    def test_story_decomposition_json_error(self, mock_client_class):
        """Test story decomposition handles JSON parsing errors."""
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON content"
        
        mock_client_instance.client.chat.completions.create.return_value = mock_response
        
        client = ImageGenerationClient("test-key")
        client.client = mock_client_instance.client
        
        story_options = StoryOptions(story_prompt="Test story")
        
        with pytest.raises(ImageError) as exc_info:
            client.decompose_story(story_options)
        
        assert "STORY_PARSING_ERROR" in str(exc_info.value)


class TestStoryGeneration:
    """Test end-to-end story generation."""
    
    @patch('src.search_service.ImageGenerationService.generate_image')
    @patch('src.client.ImageGenerationClient.decompose_story')
    def test_full_story_generation(self, mock_decompose, mock_generate):
        """Test complete story generation workflow."""
        # Setup mock story decomposition
        mock_scenes = [
            StoryScene(
                scene_number=1,
                narrative="Scene 1",
                image_prompt="Scene 1 image prompt"
            ),
            StoryScene(
                scene_number=2,
                narrative="Scene 2", 
                image_prompt="Scene 2 image prompt"
            )
        ]
        mock_decompose.return_value = mock_scenes
        
        # Setup mock image generation
        mock_image_result = Mock(spec=ImageResult)
        mock_image_result.generation_id = "test-id"
        mock_image_result.file_path = "/path/to/image.png"
        mock_generate.return_value = mock_image_result
        
        # Test story generation
        service = ImageGenerationService("test-key")
        
        story_options = StoryOptions(
            story_prompt="Test story",
            num_scenes=2
        )
        
        result = service.generate_story(story_options)
        
        # Verify results
        assert result.story_prompt == "Test story"
        assert result.num_scenes == 2
        assert result.success_rate == 100.0
        assert len(result.completed_scenes) == 2
        
        # Verify decomposition was called
        mock_decompose.assert_called_once_with(story_options)
        
        # Verify image generation was called for each scene
        assert mock_generate.call_count == 2
    
    @patch('src.search_service.ImageGenerationService.generate_image')
    @patch('src.client.ImageGenerationClient.decompose_story')
    def test_story_generation_partial_failure(self, mock_decompose, mock_generate):
        """Test story generation handles partial failures gracefully."""
        # Setup mock story decomposition
        mock_scenes = [
            StoryScene(scene_number=1, narrative="Scene 1", image_prompt="Prompt 1"),
            StoryScene(scene_number=2, narrative="Scene 2", image_prompt="Prompt 2")
        ]
        mock_decompose.return_value = mock_scenes
        
        # Setup mock image generation - first succeeds, second fails
        mock_success_result = Mock(spec=ImageResult)
        mock_generate.side_effect = [mock_success_result, Exception("Generation failed")]
        
        service = ImageGenerationService("test-key")
        story_options = StoryOptions(story_prompt="Test story", num_scenes=2)
        
        result = service.generate_story(story_options)
        
        # Should have 1 success, 1 failure
        assert result.success_rate == 50.0
        assert len(result.completed_scenes) == 1
        assert len(result.failed_scenes) == 1
    
    @patch('src.client.ImageGenerationClient.decompose_story')
    def test_story_generation_decomposition_failure(self, mock_decompose):
        """Test story generation handles decomposition failures."""
        # Setup decomposition failure
        mock_decompose.side_effect = ImageError("DECOMPOSITION_ERROR", "Failed to decompose")
        
        service = ImageGenerationService("test-key")
        story_options = StoryOptions(story_prompt="Test story")
        
        with pytest.raises(ImageError) as exc_info:
            service.generate_story(story_options)
        
        assert "DECOMPOSITION_ERROR" in str(exc_info.value)


class TestStoryIntegration:
    """Integration tests for story features."""
    
    def test_story_options_with_custom_settings(self):
        """Test story generation with custom image settings."""
        options = StoryOptions(
            story_prompt="Custom story",
            num_scenes=3,
            model="dall-e-2",
            size="512x512",
            quality="standard",
            style="natural",
            auto_save=False
        )
        
        assert options.model == "dall-e-2"
        assert options.size == "512x512"
        assert options.auto_save is False
        assert options.num_scenes == 3
    
    def test_empty_story_scenes_handling(self):
        """Test handling of empty story results."""
        story_result = StoryResult(
            story_prompt="Empty story",
            scenes=[],
            generation_time=datetime.now()
        )
        
        assert story_result.num_scenes == 0
        assert story_result.success_rate == 0.0
        assert len(story_result.all_image_urls) == 0
        assert len(story_result.get_scene_filenames()) == 0


class TestStoryFolderOrganization:
    """Test story folder organization functionality."""
    
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_next_story_folder_creation(self, mock_exists, mock_makedirs):
        """Test that story folders are created with incrementing numbers."""
        from src.search_service import ImageGenerationService
        
        # Setup mock for folder checking
        mock_exists.side_effect = lambda path: "story_1" in path  # story_1 exists, story_2 doesn't
        
        service = ImageGenerationService("test-key")
        folder_path = service._get_next_story_folder()
        
        # Should create story_2 since story_1 exists
        assert "story_2" in folder_path
        mock_makedirs.assert_called()
    
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_first_story_folder_creation(self, mock_exists, mock_makedirs):
        """Test creation of the first story folder."""
        from src.search_service import ImageGenerationService
        
        # No story folders exist yet
        mock_exists.return_value = False
        
        service = ImageGenerationService("test-key")
        folder_path = service._get_next_story_folder()
        
        # Should create story_1
        assert "story_1" in folder_path
        mock_makedirs.assert_called()
    
    @patch('src.search_service.ImageGenerationService._get_next_story_folder')
    @patch('src.search_service.ImageGenerationService.generate_image')
    @patch('src.client.ImageGenerationClient.decompose_story')
    def test_story_generation_uses_folder(self, mock_decompose, mock_generate, mock_folder):
        """Test that story generation uses the dedicated folder."""
        # Setup mocks
        mock_folder.return_value = "generated_images/story_1"
        mock_scenes = [
            StoryScene(scene_number=1, narrative="Scene 1", image_prompt="Prompt 1")
        ]
        mock_decompose.return_value = mock_scenes
        
        mock_image_result = Mock(spec=ImageResult)
        mock_image_result.file_path = "generated_images/story_1/scene1.png"
        mock_generate.return_value = mock_image_result
        
        # Test story generation
        service = ImageGenerationService("test-key")
        story_options = StoryOptions(story_prompt="Test", auto_save=True)
        
        result = service.generate_story(story_options)
        
        # Verify folder creation was called
        mock_folder.assert_called_once()
        
        # Verify generate_image was called with the story folder
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args
        assert call_args[1]['save_dir'] == "generated_images/story_1"