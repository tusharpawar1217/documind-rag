"""
LLM Client - Handle LLM API calls (Gemini, OpenAI, Claude, etc.).

This module manages interactions with Large Language Models for response generation.
"""

import os
import yaml
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

LLM_MODEL = config['llm']['model']
TEMPERATURE = config['llm']['temperature']
MAX_TOKENS = config['llm']['max_tokens']


class LLMClient:
    """Base LLM client interface."""
    
    def generate(self, prompt: str, temperature: float = TEMPERATURE, max_tokens: int = MAX_TOKENS) -> str:
        raise NotImplementedError


class GeminiLLMClient(LLMClient):
    """
    Gemini LLM client using Google's Generative AI.
    
    Handles text generation using Gemini Pro models.
    """
    
    def __init__(self):
        """Initialize Gemini LLM client."""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model_name = LLM_MODEL
        self.generation_config = {
            "temperature": TEMPERATURE,
            "top_p": config['llm']['top_p'],
            "top_k": config['llm']['top_k'],
            "max_output_tokens": MAX_TOKENS,
        }
    
    def generate(
        self,
        prompt: str,
        temperature: float = None,
        max_tokens: int = None,
        system_instruction: str = None
    ) -> str:
        """
        Generate text using Gemini.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            system_instruction: System instruction for the model
            
        Returns:
            Generated text
        """
        # Override config if provided
        gen_config = self.generation_config.copy()
        if temperature is not None:
            gen_config["temperature"] = temperature
        if max_tokens is not None:
            gen_config["max_output_tokens"] = max_tokens
        
        # Initialize model
        model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=gen_config,
            system_instruction=system_instruction
        )
        
        # Generate response
        response = model.generate_content(prompt)
        return response.text
    
    def chat(
        self,
        messages: list,
        temperature: float = None,
        system_instruction: str = None
    ) -> str:
        """
        Multi-turn chat conversation.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature
            system_instruction: System instruction
            
        Returns:
            Generated response
        """
        gen_config = self.generation_config.copy()
        if temperature is not None:
            gen_config["temperature"] = temperature
        
        model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=gen_config,
            system_instruction=system_instruction
        )
        
        # Start chat
        chat = model.start_chat(history=[])
        
        # Add messages
        for msg in messages[:-1]:  # All except last
            if msg['role'] == 'user':
                chat.send_message(msg['content'])
        
        # Send final message and get response
        response = chat.send_message(messages[-1]['content'])
        return response.text


# Global LLM client instance
llm_client = GeminiLLMClient()
