"""
Image service for fetching and caching item images
"""
import io
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
import zipfile

from PIL import Image
import requests

from ..models.game_item import ItemCategory

logger = logging.getLogger(__name__)

class ImageService:
    """Service for fetching and caching item images"""
    
    def __init__(self, zip_path: str, folder_path: str, cache_size_limit: int = 200):
        self.zip_path = Path(zip_path)
        self.folder_path = Path(folder_path)
        self.cache_size_limit = cache_size_limit
        
        self.image_cache: Dict[str, Image.Image] = {}
        self.available_images: Dict[str, str] = {}
        
        self.thumbnail_size = (64, 64)
        self.preview_size = (128, 128)
        
        self.refresh_available_images()
        
    def refresh_available_images(self):
        """Refresh the list of available images from ZIP and folder"""
        self.available_images.clear()
        
        # From ZIP
        if self.zip_path.exists():
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                for filename in zf.namelist():
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        self.available_images[Path(filename).stem] = f"zip://{filename}"
                        
        # From folder (overwrites ZIP if names conflict)
        if self.folder_path.exists():
            for file in self.folder_path.glob("**/*"):
                if file.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif'):
                    self.available_images[file.stem] = str(file.resolve())
    
    def get_image_by_name(self, name: str, category: ItemCategory, size: Optional[Tuple[int, int]] = None) -> Optional[Image.Image]:
        """Get an image by item name, with caching"""
        cache_key = f"{name}_{category.value}_{size}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        
        # Find image path
        image_path = self.available_images.get(name)
        if not image_path:
            return None
        
        try:
            if image_path.startswith("zip://"):
                with zipfile.ZipFile(self.zip_path, 'r') as zf:
                    with zf.open(image_path[6:]) as f:
                        img = Image.open(io.BytesIO(f.read()))
            else:
                img = Image.open(image_path)
            
            if size:
                img = img.resize(size, Image.Resampling.LANCZOS)
            
            # Add to cache
            if len(self.image_cache) >= self.cache_size_limit:
                self.image_cache.pop(next(iter(self.image_cache)))  # Remove oldest
            self.image_cache[cache_key] = img
            
            return img
            
        except Exception as e:
            logger.error(f"Error loading image {name}: {e}")
            return None

    def get_image_by_name_online(self, name: str, category: ItemCategory, size: Optional[Tuple[int, int]] = None) -> Optional[Image.Image]:
        """Get an image by item name from online sources, with caching"""
        # This is a placeholder for online image fetching logic
        return None

    def cache_image_for_item(self, item_id: int, name: str, category: ItemCategory, size: Optional[Tuple[int, int]] = None, cache_as: Optional[str] = None) -> Optional[Image.Image]:
        """Download and cache an online image for an item"""
        # This is a placeholder for online image fetching and caching logic
        return None

    def clear_cache(self):
        """Clear the image cache"""
        self.image_cache.clear()
        
    def close(self):
        """Clean up resources"""
        self.clear_cache()