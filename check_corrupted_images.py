"""
Check for corrupted or problematic images in dataset that cause OpenCV allocation errors.
"""
import cv2
import os
from pathlib import Path
import numpy as np

def check_image_validity(image_path):
    """Check if an image can be loaded and has valid dimensions."""
    try:
        # Use binary reading to handle Chinese paths properly
        # cv2.imread has encoding issues with Chinese characters
        im = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if im is None:
            return False, "cv2.imdecode returned None"
        
        h, w = im.shape[:2]
        
        # Check for unreasonable dimensions (likely corrupted)
        if h == 0 or w == 0:
            return False, f"Invalid dimensions: {w}x{h}"
        if h > 50000 or w > 50000:  # Unreasonably large
            return False, f"Unreasonably large: {w}x{h}"
        
        return True, f"Valid ({w}x{h})"
    except cv2.error as e:
        return False, f"OpenCV error: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def scan_dataset(dataset_dir):
    """Scan all images in dataset directory."""
    dataset_path = Path(dataset_dir)
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    
    corrupted = []
    valid = []
    
    print(f"Scanning images in {dataset_dir}...")
    
    for image_path in sorted(dataset_path.rglob('*')):
        if image_path.suffix.lower() in image_extensions:
            is_valid, status = check_image_validity(image_path)
            print(f"{'✓' if is_valid else '✗'} {image_path.relative_to(dataset_path)} - {status}")
            
            if is_valid:
                valid.append(str(image_path))
            else:
                corrupted.append((str(image_path), status))
    
    print(f"\n{'='*60}")
    print(f"Results: {len(valid)} valid, {len(corrupted)} corrupted")
    
    if corrupted:
        print(f"\nCorrupted images ({len(corrupted)}):")
        for path, reason in corrupted[:20]:  # Show first 20
            print(f"  ✗ {path}")
            print(f"    Reason: {reason}")
        if len(corrupted) > 20:
            print(f"  ... and {len(corrupted) - 20} more")

if __name__ == "__main__":
    # Scan your dataset images directory
    dataset_dir = "d:/project_workspace/最新yolo11代码/ultralytics-yolo11-main/dataset/images"
    scan_dataset(dataset_dir)
