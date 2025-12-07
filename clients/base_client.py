from abc import ABC, abstractmethod
from typing import List


class BaseLLMClient(ABC):
    """
    Abstract interface for LLM clients used by LLMExtractor.
    Implementations must provide extract_from_images() and extract_from_text().
    """

    @abstractmethod
    def extract_from_images(self, base64_images: List[str], prompt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def extract_from_text(self, text: str, prompt: str) -> str:
        raise NotImplementedError
