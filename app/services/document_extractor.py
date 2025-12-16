import os
import json
import base64
from typing import Dict, Any
from flask import current_app
from app.services.openai_client import get_openai_client, get_openai_model


class DocumentExtractor:
    
    def __init__(self):
        self.client = get_openai_client()
        self.model = get_openai_model()
    
    def allowed_file(self, filename: str) -> bool:
        allowed = current_app.config.get('ALLOWED_EXTENSIONS', set())
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed
    
    def extract_text_from_file(self, file_path: str) -> str:
        ext = file_path.rsplit('.', 1)[1].lower()
        
        if ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif ext in ['png', 'jpg', 'jpeg', 'webp']:
            with open(file_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        elif ext == 'pdf':
            return "PDF content extraction - would use PyPDF2 in production"
        
        return ""
    
    def extract_invoice_data(self, file_path: str, file_type: str) -> Dict[str, Any]:
        if file_type in ['png', 'jpg', 'jpeg', 'webp']:
            return self._extract_from_image(file_path, file_type)
        else:
            return self._extract_from_text(file_path)
    
    def _extract_from_image(self, file_path: str, file_type: str) -> Dict[str, Any]:
        with open(file_path, 'rb') as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self._get_extraction_prompt()
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{file_type};base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Extract all invoice data from this image and return as JSON."
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    def _extract_from_text(self, file_path: str) -> Dict[str, Any]:
        text_content = self.extract_text_from_file(file_path)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self._get_extraction_prompt()
                },
                {
                    "role": "user",
                    "content": f"Extract all invoice data from this text:\n\n{text_content}"
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    def _get_extraction_prompt(self) -> str:
        return """You are an expert at extracting structured data from invoices. 
        Extract the following information and return ONLY valid JSON:
        {
            "invoiceNumber": "string",
            "orderDate": "YYYY-MM-DD",
            "dueDate": "YYYY-MM-DD or null",
            "customerName": "string",
            "customerAddress": "string",
            "items": [
                {
                    "productName": "string",
                    "productDescription": "string",
                    "quantity": number,
                    "unitPrice": number,
                    "lineTotal": number
                }
            ],
            "subTotal": number,
            "taxAmount": number,
            "totalAmount": number
        }
        If a field is not found, use null or empty string. Dates should be in YYYY-MM-DD format."""

