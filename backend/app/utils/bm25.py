"""BM25 keyword scoring implementation."""

import math
from typing import List, Dict
from collections import Counter
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class BM25Scorer:
    """
    BM25 ranking algorithm for keyword-based scoring.
    
    BM25 formula:
    score = sum(IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D| / avgdl)))
    
    Where:
    - qi: query term
    - f(qi, D): term frequency in document D
    - |D|: document length
    - avgdl: average document length in corpus
    - k1: term frequency saturation parameter
    - b: length normalization parameter
    - IDF: inverse document frequency
    """
    
    def __init__(
        self,
        k1: float = None,
        b: float = None
    ):
        """
        Initialize BM25 scorer.
        
        Args:
            k1: Term frequency saturation (default 1.5)
            b: Length normalization (default 0.75)
        """
        self.k1 = k1 if k1 is not None else settings.bm25_k1
        self.b = b if b is not None else settings.bm25_b
        
        # Corpus statistics
        self.corpus_size = 0
        self.avg_doc_length = 0
        self.doc_freqs = {}  # Document frequency for each term
        
        # Validate parameters
        if self.k1 < 0:
            raise ValueError("k1 must be non-negative")
        if not 0 <= self.b <= 1:
            raise ValueError("b must be between 0 and 1")
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 scoring.
        
        Args:
            text: Input text
            
        Returns:
            List of lowercased tokens
        """
        # Simple tokenization: lowercase and split on whitespace
        # For production, use proper tokenizer (spaCy, NLTK)
        tokens = text.lower().split()
        
        # Remove very short tokens
        tokens = [t for t in tokens if len(t) > 1]
        
        return tokens
    
    def compute_idf(self, term: str, doc_freq: int) -> float:
        """
        Compute inverse document frequency for a term.
        
        IDF = log((N - df + 0.5) / (df + 0.5) + 1)
        
        Args:
            term: Query term
            doc_freq: Number of documents containing the term
            
        Returns:
            IDF score
        """
        if self.corpus_size == 0:
            return 0.0
        
        # Use smoothed IDF formula
        idf = math.log(
            (self.corpus_size - doc_freq + 0.5) /
            (doc_freq + 0.5) + 1
        )
        return max(0.0, idf)  # Ensure non-negative
    
    def score(
        self,
        query_tokens: List[str],
        doc_tokens: List[str],
        doc_length: int = None
    ) -> float:
        """
        Calculate BM25 score for a document given query.
        
        Args:
            query_tokens: Tokenized query
            doc_tokens: Tokenized document
            doc_length: Document length (defaults to len(doc_tokens))
            
        Returns:
            BM25 relevance score
        """
        if not query_tokens or not doc_tokens:
            return 0.0
        
        doc_length = doc_length or len(doc_tokens)
        
        # Use estimated average document length if not set
        if self.avg_doc_length == 0:
            self.avg_doc_length = 100  # Default estimate
        
        # Calculate term frequencies in document
        doc_term_freqs = Counter(doc_tokens)
        
        # Calculate BM25 score
        score = 0.0
        
        for query_term in query_tokens:
            if query_term not in doc_term_freqs:
                continue
            
            # Term frequency in document
            tf = doc_term_freqs[query_term]
            
            # Get document frequency (default to 1 if unknown)
            df = self.doc_freqs.get(query_term, 1)
            
            # Compute IDF
            idf = self.compute_idf(query_term, df)
            
            # Length normalization
            length_norm = 1 - self.b + self.b * (doc_length / self.avg_doc_length)
            
            # BM25 formula
            term_score = idf * (
                (tf * (self.k1 + 1)) /
                (tf + self.k1 * length_norm)
            )
            
            score += term_score
        
        return score
    
    def score_batch(
        self,
        query: str,
        documents: List[str]
    ) -> List[float]:
        """
        Score multiple documents for a query.
        
        Args:
            query: Query string
            documents: List of document strings
            
        Returns:
            List of BM25 scores
        """
        query_tokens = self.tokenize(query)
        
        scores = []
        for doc in documents:
            doc_tokens = self.tokenize(doc)
            score = self.score(query_tokens, doc_tokens)
            scores.append(score)
        
        return scores
    
    def update_corpus_stats(
        self,
        documents: List[str]
    ):
        """
        Update corpus statistics from a set of documents.
        
        Args:
            documents: List of document strings
        """
        self.corpus_size = len(documents)
        
        if self.corpus_size == 0:
            return
        
        # Calculate average document length
        total_length = 0
        doc_freqs = {}
        
        for doc in documents:
            tokens = self.tokenize(doc)
            total_length += len(tokens)
            
            # Track which documents contain each term
            unique_terms = set(tokens)
            for term in unique_terms:
                doc_freqs[term] = doc_freqs.get(term, 0) + 1
        
        self.avg_doc_length = total_length / self.corpus_size
        self.doc_freqs = doc_freqs
        
        logger.info(
            f"Updated corpus stats: {self.corpus_size} docs, "
            f"avg length {self.avg_doc_length:.1f}"
        )
    
    def normalize_score(self, score: float, max_score: float = None) -> float:
        """
        Normalize BM25 score to [0, 1] range.
        
        Args:
            score: Raw BM25 score
            max_score: Maximum score for normalization
            
        Returns:
            Normalized score
        """
        if max_score is None or max_score == 0:
            # Use heuristic: typical max score is around 10-20
            max_score = 15.0
        
        normalized = score / max_score
        return min(1.0, max(0.0, normalized))


# Global BM25 scorer instance
bm25_scorer = BM25Scorer()
