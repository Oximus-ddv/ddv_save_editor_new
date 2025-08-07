"""
Image loading and caching service for DDV Save Editor
"""
import zipfile
from pathlib import Path
from typing import Optional, Dict, Set, Tuple
import logging
from PIL import Image, ImageTk, ImageDraw, ImageFont
try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk

from ..models.game_item import ItemCategory


logger = logging.getLogger(__name__)


class ImageService:
    """Service for loading and caching item images"""
    
    def __init__(self, 
                 zip_path: str = "img.zip", 
                 folder_path: str = "img",
                 cache_size_limit: int = 200):
        self.zip_path = Path(zip_path)
        self.folder_path = Path(folder_path)
        self.cache_size_limit = cache_size_limit
        
        # Image cache: path -> PIL Image
        self._image_cache: Dict[str, Image.Image] = {}
        # PhotoImage cache for tkinter: path -> PhotoImage
        self._photo_cache: Dict[str, ImageTk.PhotoImage] = {}
        
        # Available images tracking
        self._available_images: Set[str] = set()
        self._zip_file: Optional[zipfile.ZipFile] = None
        
        # Default image sizes
        self.thumbnail_size = (64, 64)
        self.preview_size = (128, 128)
        
        self._initialize()
    
    def _initialize(self):
        """Initialize image sources and scan available images"""
        try:
            # Try to open ZIP file
            if self.zip_path.exists():
                self._zip_file = zipfile.ZipFile(self.zip_path, 'r')
                self._scan_zip_images()
                logger.info(f"Opened image ZIP: {self.zip_path}")
            
            # Scan folder images
            if self.folder_path.exists():
                self._scan_folder_images()
                logger.info(f"Scanned image folder: {self.folder_path}")
            
            logger.info(f"Found {len(self._available_images)} available images")
            
        except Exception as e:
            logger.error(f"Error initializing image service: {e}")
    
    def _scan_zip_images(self):
        """Scan images in ZIP file"""
        if not self._zip_file:
            return
        
        for file_info in self._zip_file.filelist:
            if not file_info.is_dir() and self._is_image_file(file_info.filename):
                # Normalize path separators
                normalized_path = file_info.filename.replace('\\', '/')
                self._available_images.add(normalized_path)
    
    def _scan_folder_images(self):
        """Scan images in folder structure"""
        if not self.folder_path.exists():
            return
        
        for image_file in self.folder_path.rglob("*"):
            if image_file.is_file() and self._is_image_file(image_file.name):
                # Get relative path from folder root
                relative_path = image_file.relative_to(self.folder_path)
                normalized_path = str(relative_path).replace('\\', '/')
                self._available_images.add(normalized_path)
    
    def _is_image_file(self, filename: str) -> bool:
        """Check if file is a supported image format"""
        ext = Path(filename).suffix.lower()
        return ext in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
    
    def get_item_image(self, 
                      item_id: int, 
                      category: ItemCategory, 
                      size: Tuple[int, int] = None,
                      for_tkinter: bool = False) -> Optional[Image.Image]:
        """
        Get image for an item by ID and category
        
        Args:
            item_id: The item ID
            category: Item category
            size: Desired image size (width, height). If None, uses thumbnail_size
            for_tkinter: If True, returns PhotoImage for tkinter
        """
        if size is None:
            size = self.thumbnail_size
        
        # Generate possible image paths
        possible_paths = self._generate_image_paths(item_id, category)
        
        # Try to find and load image
        for path in possible_paths:
            image = self._load_image(path, size)
            if image:
                if for_tkinter:
                    return self._get_photo_image(path, image)
                return image
        
        # Return placeholder if no image found
        placeholder = self._create_placeholder_image(size, str(item_id))
        if for_tkinter:
            return ImageTk.PhotoImage(placeholder)
        return placeholder
    
    def get_image_by_path(self, 
                         image_path: str, 
                         size: Tuple[int, int] = None,
                         for_tkinter: bool = False) -> Optional[Image.Image]:
        """Get image by specific path"""
        if size is None:
            size = self.thumbnail_size
        
        image = self._load_image(image_path, size)
        if image:
            if for_tkinter:
                return self._get_photo_image(image_path, image)
            return image
        
        # Return placeholder
        placeholder = self._create_placeholder_image(size, "?")
        if for_tkinter:
            return ImageTk.PhotoImage(placeholder)
        return placeholder
    
    def _generate_image_paths(self, item_id: int, category: ItemCategory) -> list[str]:
        """Generate possible image paths for an item"""
        paths = []
        category_name = category.value
        
        # Common image extensions
        extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
        
        for ext in extensions:
            # Category folder variations
            paths.extend([
                f"{category_name}/{item_id}{ext}",
                f"{category_name.rstrip('s')}/{item_id}{ext}",  # Remove 's' (pets -> pet)
                f"{category_name}/{category_name[:-1]}_{item_id}{ext}",  # pet_12345.png
            ])
            
            # Root level
            paths.extend([
                f"{item_id}{ext}",
                f"{category_name}_{item_id}{ext}",
            ])
        
        return paths
    
    def _load_image(self, image_path: str, size: Tuple[int, int]) -> Optional[Image.Image]:
        """Load an image from ZIP or file system"""
        # Check cache first
        cache_key = f"{image_path}_{size[0]}x{size[1]}"
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        
        try:
            image = None
            
            # Try ZIP file first
            if self._zip_file and image_path in self._available_images:
                with self._zip_file.open(image_path) as img_file:
                    image = Image.open(img_file)
                    image.load()  # Ensure image is fully loaded
            
            # Try file system
            elif image_path in self._available_images:
                file_path = self.folder_path / image_path
                if file_path.exists():
                    image = Image.open(file_path)
            
            if image:
                # Resize if needed
                if image.size != size:
                    image = image.resize(size, Image.Resampling.LANCZOS)
                
                # Cache the image (with size limit)
                if len(self._image_cache) < self.cache_size_limit:
                    self._image_cache[cache_key] = image.copy()
                
                return image
            
        except Exception as e:
            logger.debug(f"Could not load image {image_path}: {e}")
        
        return None
    
    def _get_photo_image(self, path: str, pil_image: Image.Image) -> ImageTk.PhotoImage:
        """Convert PIL Image to PhotoImage for tkinter"""
        cache_key = f"photo_{path}_{pil_image.size[0]}x{pil_image.size[1]}"
        
        if cache_key in self._photo_cache:
            return self._photo_cache[cache_key]
        
        photo = ImageTk.PhotoImage(pil_image)
        
        # Cache with size limit
        if len(self._photo_cache) < self.cache_size_limit:
            self._photo_cache[cache_key] = photo
        
        return photo
    
    def _create_placeholder_image(self, size: Tuple[int, int], text: str = "?") -> Image.Image:
        """Create a placeholder image for missing items"""
        # Create image with light gray background
        image = Image.new('RGBA', size, (240, 240, 240, 255))
        draw = ImageDraw.Draw(image)
        
        # Draw border
        border_color = (200, 200, 200, 255)
        draw.rectangle([0, 0, size[0]-1, size[1]-1], outline=border_color, width=2)
        
        # Draw text
        try:
            # Try to use a reasonable font size
            font_size = min(size) // 3
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        if font:
            text_color = (128, 128, 128, 255)
            
            # Get text size and center it
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
            
            draw.text((x, y), text, fill=text_color, font=font)
        
        return image
    
    def preload_category_images(self, category: ItemCategory, item_ids: list[int]) -> None:
        """Preload images for a category to improve performance"""
        logger.info(f"Preloading images for {category.value}: {len(item_ids)} items")
        
        # Load in batches to avoid memory issues
        batch_size = 20
        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i:i + batch_size]
            for item_id in batch:
                # Just call get_item_image to populate cache
                self.get_item_image(item_id, category)
    
    def clear_cache(self) -> None:
        """Clear image caches to free memory"""
        self._image_cache.clear()
        self._photo_cache.clear()
        logger.info("Image cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "cached_images": len(self._image_cache),
            "cached_photos": len(self._photo_cache),
            "available_images": len(self._available_images),
            "cache_limit": self.cache_size_limit
        }
    
    def refresh_available_images(self) -> None:
        """Refresh the list of available images"""
        self._available_images.clear()
        
        if self._zip_file:
            try:
                self._zip_file.close()
            except:
                pass
            self._zip_file = None
        
        self._initialize()
    
    def close(self) -> None:
        """Clean up resources"""
        if self._zip_file:
            self._zip_file.close()
        self.clear_cache()
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.close()
        except:
            pass
