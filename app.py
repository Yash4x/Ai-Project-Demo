"""
🌐 AI Image Generation Web Interface
===================================

A modern, sleek web interface for AI image generation using Flask.
Features single image generation and visual story creation.
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from flask_cors import CORS
from dotenv import load_dotenv

from src.search_service import ImageGenerationService
from src.models import ImageOptions, StoryOptions, ImageResult, StoryResult
from src.logging_config import setup_logging, get_logger

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Set up logging
setup_logging()
logger = get_logger(__name__)

# Initialize the image generation service
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")

service = ImageGenerationService(api_key=api_key)

# Ensure directories exist
os.makedirs("generated_images", exist_ok=True)
os.makedirs("static/generated", exist_ok=True)  # For web-accessible images


@app.route('/')
def index():
    """Homepage with clean, modern design."""
    return render_template('index.html')


@app.route('/generate')
def generate_page():
    """Single image generation page."""
    return render_template('generate.html')


@app.route('/story')
def story_page():
    """Visual story generation page."""
    return render_template('story.html')


@app.route('/gallery')
def gallery_page():
    """Gallery page to view all generated content."""
    return render_template('gallery.html')


@app.route('/api/generate-image', methods=['POST'])
def api_generate_image():
    """API endpoint for single image generation."""
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Prompt is required'}), 400
        
        prompt = data['prompt'].strip()
        if not prompt:
            return jsonify({'error': 'Prompt cannot be empty'}), 400
        
        # Create image options
        options = ImageOptions(
            size=data.get('size', '1024x1024'),
            quality=data.get('quality', 'standard'),
            style=data.get('style', 'vivid')
        )
        
        logger.info(f"Generating single image for prompt: {prompt}")
        
        # Track timing
        start_time = datetime.now()
        
        # Generate the image
        result = service.generate_image(
            prompt=prompt,
            options=options,
            auto_save=True,
            save_dir="generated_images"
        )
        
        # Calculate generation time
        generation_time = (datetime.now() - start_time).total_seconds()
        
        # Copy to web-accessible location
        web_path = _copy_to_web_accessible(result.file_path, "single_image")
        
        response_data = {
            'success': True,
            'image_url': result.image_url,
            'file_path': result.file_path,
            'web_path': web_path,
            'revised_prompt': result.metadata.revised_prompt if result.metadata else None,
            'generation_time': generation_time,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Single image generated successfully: {result.file_path}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error generating single image: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-story', methods=['POST'])
def api_generate_story():
    """API endpoint for story generation."""
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Prompt is required'}), 400
        
        prompt = data['prompt'].strip()
        if not prompt:
            return jsonify({'error': 'Prompt cannot be empty'}), 400
        
        # Create story options
        options = StoryOptions(
            story_prompt=prompt,
            num_scenes=int(data.get('num_scenes', 5)),
            size=data.get('image_size', '1024x1024'),
            quality=data.get('image_quality', 'standard'),
            style=data.get('image_style', 'vivid'),
            enable_narration=bool(data.get('enable_narration', False)),
            voice=data.get('voice', 'alloy'),
            narration_speed=float(data.get('narration_speed', 1.0))
        )
        
        logger.info(f"Generating story for prompt: {prompt}")
        
        # Generate the story
        result = service.generate_story(options)
        
        # Determine story folder from the first scene's file path
        story_folder_name = "story_unknown"
        if result.scenes and result.scenes[0].image_result and result.scenes[0].image_result.file_path:
            # Extract folder name from file path (e.g., "generated_images/story_5/file.png" -> "story_5")
            import os
            folder_path = os.path.dirname(result.scenes[0].image_result.file_path)
            story_folder_name = os.path.basename(folder_path)
        
        # Copy all scene images to web-accessible location
        web_scenes = []
        for scene in result.scenes:
            if scene.image_result and scene.image_result.file_path:
                web_path = _copy_to_web_accessible(
                    scene.image_result.file_path, 
                    story_folder_name
                )
                # Create audio URL if audio file exists
                audio_url = None
                if scene.audio_file_path and os.path.exists(scene.audio_file_path):
                    # Convert absolute path to relative URL
                    audio_relative_path = os.path.relpath(scene.audio_file_path, 'generated_images')
                    audio_url = f"/audio/{audio_relative_path}"
                
                web_scenes.append({
                    'scene_number': scene.scene_number,
                    'description': scene.narrative,  # Use narrative instead of description
                    'web_path': web_path,
                    'file_path': scene.image_result.file_path,
                    'audio_url': audio_url,
                    'has_audio': scene.has_audio,
                    'revised_prompt': scene.image_result.metadata.revised_prompt if scene.image_result.metadata else None,
                    'generation_time': 0  # Story generation timing is tracked at story level
                })
        
        response_data = {
            'success': True,
            'story_folder': story_folder_name,
            'total_scenes': result.num_scenes,
            'successful_scenes': len(result.completed_scenes),
            'success_rate': result.success_rate,
            'scenes': web_scenes,
            'total_generation_time': result.total_generation_time,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Story generated successfully: {story_folder_name}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error generating story: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/gallery')
def api_gallery():
    """Get list of all generated images and stories."""
    try:
        gallery_items = []
        
        # Scan generated_images directory
        if os.path.exists("generated_images"):
            for item in os.listdir("generated_images"):
                item_path = os.path.join("generated_images", item)
                
                if os.path.isdir(item_path):
                    # This is a story folder
                    story_info = _get_story_info(item_path)
                    if story_info:
                        gallery_items.append(story_info)
                elif item.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    # This is a single image
                    image_info = _get_image_info(item_path)
                    if image_info:
                        gallery_items.append(image_info)
        
        # Sort by creation time (newest first)
        gallery_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({'items': gallery_items})
        
    except Exception as e:
        logger.error(f"Error getting gallery: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve generated images from web-accessible location."""
    return send_from_directory('static/generated', filename)


@app.route('/generated_images/<path:filename>')
def serve_generated_image(filename):
    """Serve images directly from generated_images directory."""
    return send_from_directory('generated_images', filename)


@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """Serve audio files from generated_images directory."""
    return send_from_directory('generated_images', filename)


def _copy_to_web_accessible(source_path: str, folder_name: str) -> str:
    """Copy generated image to web-accessible location."""
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source image not found: {source_path}")
    
    # Create unique filename to avoid conflicts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{folder_name}_{timestamp}_{os.path.basename(source_path)}"
    
    # Ensure destination directory exists
    dest_dir = "static/generated"
    os.makedirs(dest_dir, exist_ok=True)
    
    # Copy file
    dest_path = os.path.join(dest_dir, filename)
    shutil.copy2(source_path, dest_path)
    
    # Return web-accessible URL - use relative path that works in browser
    return f"/images/{filename}"


def _get_story_info(story_path: str) -> Optional[Dict]:
    """Get information about a story folder."""
    try:
        story_name = os.path.basename(story_path)
        scenes = []
        audio_files = {}
        
        # First pass: collect all audio files by scene number
        for file in os.listdir(story_path):
            if file.endswith('.mp3') and 'narration' in file:
                # Extract scene number from filename like "scene_1_narration.mp3"
                parts = file.split('_')
                if len(parts) >= 2 and parts[0] == 'scene':
                    try:
                        scene_num = int(parts[1])
                        audio_files[scene_num] = {
                            'filename': file,
                            'path': os.path.join(story_path, file),
                            'url': f"/audio/{story_name}/{file}"
                        }
                    except (ValueError, IndexError):
                        continue
        
        # Second pass: get all image files and match with audio
        for file in os.listdir(story_path):
            if file.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                file_path = os.path.join(story_path, file)
                
                # Try to determine scene number from image filename
                scene_number = len(scenes) + 1  # Default scene numbering
                
                scene_data = {
                    'filename': file,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    'scene_number': scene_number,
                    'has_audio': scene_number in audio_files,
                    'audio_url': audio_files.get(scene_number, {}).get('url'),
                    'audio_filename': audio_files.get(scene_number, {}).get('filename')
                }
                scenes.append(scene_data)
        
        if not scenes:
            return None
        
        # Sort scenes by filename (should be in order)
        scenes.sort(key=lambda x: x['filename'])
        
        # Count total audio files
        total_audio_files = len(audio_files)
        
        return {
            'type': 'story',
            'name': story_name,
            'path': story_path,
            'scene_count': len(scenes),
            'scenes': scenes,
            'has_narration': total_audio_files > 0,
            'audio_count': total_audio_files,
            'created_at': min(scene['modified'] for scene in scenes),
            'size': sum(scene['size'] for scene in scenes)
        }
        
    except Exception as e:
        logger.error(f"Error getting story info for {story_path}: {str(e)}")
        return None


def _get_image_info(image_path: str) -> Optional[Dict]:
    """Get information about a single image."""
    try:
        filename = os.path.basename(image_path)
        stat = os.stat(image_path)
        
        return {
            'type': 'image',
            'name': filename,
            'path': image_path,
            'size': stat.st_size,
            'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting image info for {image_path}: {str(e)}")
        return None


if __name__ == '__main__':
    print("🌐 Starting AI Image Generation Web Interface...")
    print("📖 Access the application at: http://localhost:5000")
    print("🎨 Features: Single Images • Visual Stories • Gallery")
    print("✨ Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5000)