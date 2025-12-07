from typing import List
import google.generativeai as genai
from clients.base_client import BaseLLMClient


class GeminiClient(BaseLLMClient):

    def __init__(self, api_key: str, model: str = "gemini-2.5-pro"):
        genai.configure(api_key=api_key)
        self.model = model
        self.client = genai.GenerativeModel(model)

    def extract_from_images(self, base64_images: List[str], prompt: str) -> str:
        content = [prompt]

        for base64_image in base64_images:
            image_data = {
                "mime_type": "image/png",
                "data": base64_image
            }
            content.append(image_data)

        # Disable safety settings to prevent blocking of form data
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ]

        response = self.client.generate_content(content, safety_settings=safety_settings)
        return response.text

    def extract_from_text(self, text: str, prompt: str) -> str:
        content = [prompt, f"\n\nDocument Content:\n{text}"]
        
        # Disable safety settings
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ]

        response = self.client.generate_content(content, safety_settings=safety_settings)
        print("response from LLM")
        print(response.text)
        return response.text
