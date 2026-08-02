"""
Test Data Generator
Generates synthetic Q&A pairs from documents for evaluation.
"""

from typing import List, Dict, Tuple
import random


class TestDataGenerator:
    """Generates evaluation test sets from document chunks."""
    
    def __init__(self):
        self.test_queries = []
    
    def generate_synthetic_qa(self, chunks: List[Dict]) -> List[Dict]:
        """
        Generate synthetic Q&A pairs from chunks.
        Bootstrap ground truth for evaluation.
        
        Args:
            chunks: List of document chunks with content and metadata
            
        Returns:
            List of test queries with ground truth
        """
        test_set = []
        
        for chunk in chunks:
            content = chunk['content']
            chunk_id = chunk['chunk_id']
            
            # Skip very short chunks
            if len(content) < 100:
                continue
            
            # Generate different query types
            queries = self._generate_queries_from_chunk(content, chunk)
            
            for query in queries:
                test_set.append({
                    'query': query['question'],
                    'query_type': query['type'],
                    'relevant_chunks': {chunk_id},  # Ground truth
                    'expected_page': chunk.get('page_number'),
                    'context': content[:500],  # Preview for validation
                })
        
        return test_set
    
    def _generate_queries_from_chunk(self, content: str, metadata: Dict) -> List[Dict]:
        """Generate various query types from a chunk."""
        queries = []
        
        # Extract first sentence for fact-based queries
        sentences = [s.strip() + '.' for s in content.split('.') if s.strip()]
        if not sentences:
            return queries
        
        first_sentence = sentences[0]
        content_lower = content.lower()
        
        # Query type 1: Definition/Explanation
        if any(word in content_lower for word in ['is', 'are', 'defined as', 'refers to']):
            # Extract subject
            words = first_sentence.split()
            if len(words) > 3:
                subject = ' '.join(words[:min(4, len(words))])
                queries.append({
                    'question': f"What is {subject.lower()}?",
                    'type': 'definition'
                })
        
        # Query type 2: How-to/Process
        if any(word in content_lower for word in ['steps', 'process', 'method', 'procedure', 'how to']):
            queries.append({
                'question': f"How to {self._extract_action(content)}?",
                'type': 'how-to'
            })
        
        # Query type 3: List/Enumeration
        if any(word in content_lower for word in ['following', 'includes', 'list', 'types']):
            queries.append({
                'question': f"List the {self._extract_topic(content)}",
                'type': 'enumeration'
            })
        
        # Query type 4: Factual
        # Look for numbers, dates, names
        import re
        numbers = re.findall(r'\b\d+\b', content)
        if numbers:
            queries.append({
                'question': f"What is the number mentioned in {self._extract_topic(content)}?",
                'type': 'factual'
            })
        
        # Query type 5: Location-based (if page number available)
        if metadata.get('page_number'):
            page = metadata['page_number']
            queries.append({
                'question': f"Information from page {page}",
                'type': 'location'
            })
        
        return queries[:2]  # Limit to 2 queries per chunk
    
    def _extract_action(self, content: str) -> str:
        """Extract action verb from content."""
        action_words = ['configure', 'install', 'setup', 'create', 'use', 'implement']
        content_lower = content.lower()
        
        for action in action_words:
            if action in content_lower:
                return action
        
        return "perform the task"
    
    def _extract_topic(self, content: str) -> str:
        """Extract main topic from content."""
        # Simple heuristic: take first few words
        words = content.split()[:10]
        topic_words = [w for w in words if len(w) > 4 and w[0].isupper()]
        
        if topic_words:
            return ' '.join(topic_words[:3]).lower()
        return "items"
    
    def load_default_test_queries(self) -> List[Dict]:
        """
        Load a default set of test queries for common scenarios.
        Use this when you don't have documents to generate from.
        """
        return [
            {
                'query': 'What is the main topic of this document?',
                'query_type': 'general',
                'relevant_chunks': None,  # Will be determined during eval
                'expected_page': None
            },
            {
                'query': 'What is the methodology used?',
                'query_type': 'explanation',
                'relevant_chunks': None,
                'expected_page': None
            },
            {
                'query': 'What are the results?',
                'query_type': 'factual',
                'relevant_chunks': None,
                'expected_page': None
            },
            {
                'query': 'How was the data collected?',
                'query_type': 'how-to',
                'relevant_chunks': None,
                'expected_page': None
            },
            {
                'query': 'List all the findings',
                'query_type': 'enumeration',
                'relevant_chunks': None,
                'expected_page': None
            },
            {
                'query': 'Who are the authors?',
                'query_type': 'entity',
                'relevant_chunks': None,
                'expected_page': None
            },
            {
                'query': 'When was this published?',
                'query_type': 'temporal',
                'relevant_chunks': None,
                'expected_page': None
            },
            {
                'query': 'What are the conclusions?',
                'query_type': 'factual',
                'relevant_chunks': None,
                'expected_page': None
            },
        ]
    
    def create_golden_set(
        self,
        num_queries: int = 50,
        chunks: List[Dict] = None
    ) -> List[Dict]:
        """
        Create a golden evaluation set.
        
        Args:
            num_queries: Number of test queries to generate
            chunks: Document chunks to generate from
            
        Returns:
            List of test queries with ground truth
        """
        if chunks:
            # Generate from actual documents
            synthetic = self.generate_synthetic_qa(chunks)
            # Mix with default queries
            default = self.load_default_test_queries()
            combined = synthetic + default
            
            # Shuffle and limit
            random.shuffle(combined)
            return combined[:num_queries]
        else:
            # Use default queries only
            return self.load_default_test_queries()
