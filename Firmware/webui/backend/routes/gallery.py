"""Photo gallery endpoints"""
from flask import Blueprint, jsonify, send_file
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from mothbox_paths import PHOTOS_DIR

gallery_bp = Blueprint('gallery', __name__)

@gallery_bp.route('/photos', methods=['GET'])
def list_photos():
    """List all photos with metadata"""
    try:
        if not PHOTOS_DIR.exists():
            return jsonify({'photos': []})

        photos = []
        for photo_path in sorted(PHOTOS_DIR.glob('**/*.jpg'), key=lambda p: p.stat().st_mtime, reverse=True):
            stat = photo_path.stat()
            photos.append({
                'path': str(photo_path.relative_to(PHOTOS_DIR)),
                'filename': photo_path.name,
                'size': stat.st_size,
                'timestamp': stat.st_mtime,
                'date': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

        return jsonify({'photos': photos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gallery_bp.route('/photo/<path:photo_path>', methods=['GET'])
def get_photo(photo_path):
    """Serve a specific photo"""
    try:
        full_path = PHOTOS_DIR / photo_path
        if not full_path.exists() or not str(full_path).startswith(str(PHOTOS_DIR)):
            return jsonify({'error': 'Photo not found'}), 404

        return send_file(full_path, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gallery_bp.route('/thumbnail/<path:photo_path>', methods=['GET'])
def get_thumbnail(photo_path):
    """Get thumbnail for a photo (generates if needed)"""
    try:
        from PIL import Image
        import io

        full_path = PHOTOS_DIR / photo_path
        if not full_path.exists() or not str(full_path).startswith(str(PHOTOS_DIR)):
            return jsonify({'error': 'Photo not found'}), 404

        # Generate thumbnail
        img = Image.open(full_path)
        img.thumbnail((300, 300))

        # Return as bytes
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG', quality=85)
        img_io.seek(0)

        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500
