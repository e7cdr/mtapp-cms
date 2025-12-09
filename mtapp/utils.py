import secrets
import string
import os
import logging
from django.conf import settings
import fitz

logger = logging.getLogger(__name__)


def generate_code_id(prefix):
    characters = string.ascii_uppercase + string.digits
    random_code = ''.join(secrets.choice(characters) for _ in range(6))
    return f"{prefix}-{random_code}"


def convert_pdf_to_images(pdf_path, output_dir, tour_id):
    """Convert PDF pages to PNG images for carousel display."""
    try:
        logger.debug(f"Converting PDF: {pdf_path}, Output: {output_dir}, Tour ID: {tour_id}")
        # Check PDF accessibility
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file does not exist: {pdf_path}")
            return []
        if not os.access(pdf_path, os.R_OK):
            logger.error(f"No read permission for PDF: {pdf_path}")
            return []
        # Check output directory
        os.makedirs(output_dir, exist_ok=True)
        if not os.access(output_dir, os.W_OK):
            logger.error(f"No write permission for output dir: {output_dir}")
            return []
        # Open PDF
        pdf_document = fitz.open(pdf_path)
        if pdf_document.page_count == 0:
            logger.error(f"PDF has no pages: {pdf_path}")
            pdf_document.close()
            return []
        image_paths = []
        for page_num in range(min(pdf_document.page_count, 5)):  # Limit to 5 pages
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))  # 1x zoom
            image_path = os.path.join(output_dir, f'page_{page_num + 1}.png')
            pix.save(image_path)
            relative_path = os.path.join(f'tour_{tour_id}_pdf_images', f'page_{page_num + 1}.png')
            media_url_path = f'{settings.MEDIA_URL}{relative_path}'
            if not os.path.exists(image_path):
                logger.error(f"Failed to create image: {image_path}")
                continue
            image_paths.append(media_url_path)
            logger.debug(f"Generated image: {image_path}, URL: {media_url_path}")
        pdf_document.close()
        logger.info(f"Successfully converted PDF to {len(image_paths)} images for tour {tour_id}")
        return image_paths
    except Exception as e:
        logger.error(f"Error converting PDF to images for tour {tour_id}: {str(e)}")
        return []
