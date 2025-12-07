import base64
from io import BytesIO
from pathlib import Path
from typing import List, Union, Dict, Any
import pypdfium2 as pdfium
import pdfplumber
from pypdf import PdfReader
from PIL import Image


class PDFProcessor:

    @staticmethod
    def pdf_to_images(pdf_path: Union[str, Path], dpi: int = 300) -> List[Image.Image]:
        pdf = pdfium.PdfDocument(pdf_path)
        images = []
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=dpi/72)
            pil_image = bitmap.to_pil()
            images.append(pil_image)
        return images

    @staticmethod
    def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
        buffered = BytesIO()
        image.save(buffered, format=format)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str

    @staticmethod
    def prepare_images_for_llm(pdf_path: Union[str, Path]) -> List[str]:
        images = PDFProcessor.pdf_to_images(pdf_path)
        base64_images = [
            PDFProcessor.image_to_base64(img) for img in images
        ]
        return base64_images

    @staticmethod
    def load_image_as_base64(image_path: Union[str, Path]) -> str:
        with Image.open(image_path) as img:
            return PDFProcessor.image_to_base64(img)

    @staticmethod
    def extract_form_fields(pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract form fields from PDF AcroForm."""
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()
        
        if fields is None:
            return {}
        
        # Extract field names and values
        form_data = {}
        for field_name, field_obj in fields.items():
            # Get the field value
            value = field_obj.get('/V')
            
            # Handle different value types
            if value is not None:
                # Convert from PDF object to string if needed
                if hasattr(value, 'get_object'):
                    value = value.get_object()
                form_data[field_name] = str(value) if value else ""
            else:
                form_data[field_name] = ""
        
        return form_data
    
    @staticmethod
    def extract_text(pdf_path: Union[str, Path], include_form_fields: bool = True) -> str:
        """Extract text from PDF, optionally including form field data."""
        text_content = []
        
        # Extract regular text with pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract text with layout preservation
                text = page.extract_text(layout=True)
                if text:
                    text_content.append(text)
        
        # Extract form fields if requested
        if include_form_fields:
            form_fields = PDFProcessor.extract_form_fields(pdf_path)
            if form_fields:
                # Add form fields as structured data
                form_text = ["\n=== PDF FORM FIELDS ==="]
                for field_name, field_value in form_fields.items():
                    if field_value:  # Only include non-empty fields
                        form_text.append(f"{field_name}: {field_value}")
                text_content.append("\n".join(form_text))
        
        return "\n\n".join(text_content)
