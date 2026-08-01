"""
Prompts - Store and manage prompt templates for LLM interactions.

This module contains all prompt templates used for RAG question answering.
"""

import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

SYSTEM_ROLE = config['prompts']['system_role']


class PromptTemplates:
    """Collection of prompt templates for RAG."""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get the system prompt that defines the AI's role."""
        return SYSTEM_ROLE
    
    @staticmethod
    def get_rag_prompt(context: str, question: str) -> str:
        """
        Generate RAG prompt with context and question.
        
        Args:
            context: Retrieved context from documents
            question: User's question
            
        Returns:
            Formatted prompt string
        """
        return f"""Answer the following question based on the provided context. 
If the answer is not in the context, say "I don't have enough information to answer that question."

Context:
{context}

Question: {question}

Answer:"""
    
    @staticmethod
    def get_chat_prompt(history: list, question: str) -> str:
        """
        Generate conversational prompt with history.
        
        Args:
            history: Previous conversation turns
            question: Current question
            
        Returns:
            Formatted prompt string
        """
        history_text = "\n".join([
            f"User: {turn['user']}\nAssistant: {turn['assistant']}"
            for turn in history
        ])
        
        return f"""{history_text}

User: {question}
Assistant:"""
    
    @staticmethod
    def get_summary_prompt(text: str, max_length: int = 200) -> str:
        """
        Generate summarization prompt.
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length
            
        Returns:
            Formatted prompt string
        """
        return f"""Summarize the following text in no more than {max_length} words:

{text}

Summary:"""


# Global prompt templates instance
prompts = PromptTemplates()
