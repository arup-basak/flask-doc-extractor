from openai import OpenAI
from flask import current_app


class OpenAIClient:
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OpenAIClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        api_key = current_app.config.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            )
        self._client = OpenAI(api_key=api_key)
    
    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._initialize_client()
        return self._client
    
    @property
    def model(self) -> str:
        return current_app.config.get('OPENAI_MODEL', 'gpt-4o-mini')
    
    def is_configured(self) -> bool:
        api_key = current_app.config.get('OPENAI_API_KEY')
        return bool(api_key)


def get_openai_client() -> OpenAI:
    client_wrapper = OpenAIClient()
    return client_wrapper.client


def get_openai_model() -> str:
    client_wrapper = OpenAIClient()
    return client_wrapper.model

