"""
Generation Evaluation Metrics
Measures quality of LLM-generated answers given correct context.
"""

from typing import List, Dict
import re


class GenerationEvaluator:
    """Evaluates generation quality (faithfulness, relevance, correctness)."""
    
    def __init__(self):
        self.results = []
    
    def faithfulness_score(self, answer: str, context: str) -> Dict[str, any]:
        """
        Faithfulness / Groundedness - Is every claim supported by context?
        Checks if answer hallucinates beyond retrieved context.
        
        Simple heuristic version (use LLM-as-judge for production).
        
        Args:
            answer: Generated answer
            context: Retrieved context chunks
            
        Returns:
            Dict with score and analysis
        """
        # Split answer into claims (sentences)
        sentences = [s.strip() for s in re.split(r'[.!?]+', answer) if s.strip()]
        
        supported_count = 0
        unsupported_claims = []
        
        context_lower = context.lower()
        
        for sentence in sentences:
            # Extract key terms from sentence
            words = sentence.lower().split()
            key_words = [w for w in words if len(w) > 3]
            
            # Check if most key words appear in context
            matches = sum(1 for word in key_words if word in context_lower)
            
            if len(key_words) > 0 and matches / len(key_words) >= 0.5:
                supported_count += 1
            else:
                unsupported_claims.append(sentence)
        
        score = supported_count / len(sentences) if sentences else 0.0
        
        return {
            'score': score,
            'total_claims': len(sentences),
            'supported_claims': supported_count,
            'unsupported_claims': unsupported_claims,
            'interpretation': self._interpret_faithfulness(score)
        }
    
    def answer_relevance_score(self, answer: str, query: str) -> Dict[str, any]:
        """
        Answer Relevance - Does answer actually address the query?
        
        Simple heuristic version (use LLM-as-judge for production).
        
        Args:
            answer: Generated answer
            query: User query
            
        Returns:
            Dict with score and analysis
        """
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would'}
        
        query_keywords = query_words - stop_words
        answer_keywords = answer_words - stop_words
        
        if not query_keywords:
            return {'score': 0.0, 'interpretation': 'Invalid query'}
        
        # Check keyword overlap
        overlap = query_keywords.intersection(answer_keywords)
        coverage = len(overlap) / len(query_keywords)
        
        # Check if answer is addressing the query type
        query_lower = query.lower()
        answer_lower = answer.lower()
        
        type_match = False
        if any(word in query_lower for word in ['what', 'which', 'who']):
            # Should define/identify something
            type_match = len(answer) > 20  # Has substantial content
        elif 'how' in query_lower:
            # Should explain process/method
            type_match = any(word in answer_lower for word in ['step', 'process', 'method', 'by'])
        elif 'why' in query_lower:
            # Should explain reason
            type_match = any(word in answer_lower for word in ['because', 'reason', 'due to', 'since'])
        else:
            type_match = True  # General query
        
        # Combine scores
        score = (coverage * 0.7) + (0.3 if type_match else 0.0)
        
        return {
            'score': min(score, 1.0),
            'keyword_coverage': coverage,
            'type_match': type_match,
            'matched_keywords': list(overlap),
            'interpretation': self._interpret_relevance(score)
        }
    
    def answer_correctness(
        self,
        answer: str,
        ground_truth: str,
        check_factual_fields: bool = True
    ) -> Dict[str, any]:
        """
        Answer Correctness - Compare against gold answer.
        
        Args:
            answer: Generated answer
            ground_truth: Expected correct answer
            check_factual_fields: Check for dates, numbers, etc.
            
        Returns:
            Dict with score and analysis
        """
        # Simple token overlap (BLEU-like, but simplified)
        answer_tokens = set(answer.lower().split())
        truth_tokens = set(ground_truth.lower().split())
        
        if not truth_tokens:
            return {'score': 0.0, 'interpretation': 'No ground truth'}
        
        overlap = answer_tokens.intersection(truth_tokens)
        
        # Precision and recall
        precision = len(overlap) / len(answer_tokens) if answer_tokens else 0.0
        recall = len(overlap) / len(truth_tokens)
        
        # F1 score
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0
        
        # Extract and check factual fields (dates, numbers)
        factual_match = True
        if check_factual_fields:
            answer_numbers = set(re.findall(r'\b\d+\b', answer))
            truth_numbers = set(re.findall(r'\b\d+\b', ground_truth))
            
            answer_dates = set(re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', answer))
            truth_dates = set(re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', ground_truth))
            
            if truth_numbers and not answer_numbers.intersection(truth_numbers):
                factual_match = False
            if truth_dates and not answer_dates.intersection(truth_dates):
                factual_match = False
        
        # Adjust score if factual mismatch
        final_score = f1 * (1.0 if factual_match else 0.5)
        
        return {
            'score': final_score,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'factual_match': factual_match,
            'interpretation': self._interpret_correctness(final_score)
        }
    
    def evaluate_answer(
        self,
        query: str,
        answer: str,
        context: str,
        ground_truth: str = None
    ) -> Dict[str, any]:
        """
        Comprehensive evaluation of a single answer.
        
        Args:
            query: User query
            answer: Generated answer
            context: Retrieved context
            ground_truth: Optional gold answer
            
        Returns:
            Dict with all metrics
        """
        results = {
            'query': query,
            'answer_length': len(answer),
            'context_length': len(context)
        }
        
        # Faithfulness
        faithfulness = self.faithfulness_score(answer, context)
        results['faithfulness'] = faithfulness['score']
        results['faithfulness_details'] = faithfulness
        
        # Relevance
        relevance = self.answer_relevance_score(answer, query)
        results['relevance'] = relevance['score']
        results['relevance_details'] = relevance
        
        # Correctness (if ground truth available)
        if ground_truth:
            correctness = self.answer_correctness(answer, ground_truth)
            results['correctness'] = correctness['score']
            results['correctness_details'] = correctness
        
        self.results.append(results)
        return results
    
    def _interpret_faithfulness(self, score: float) -> str:
        """Interpret faithfulness score."""
        if score >= 0.9:
            return "✅ EXCELLENT - No hallucinations detected"
        elif score >= 0.7:
            return "✓ GOOD - Minor unsupported claims"
        elif score >= 0.5:
            return "⚠ FAIR - Some hallucinations present"
        else:
            return "❌ POOR - Significant hallucinations"
    
    def _interpret_relevance(self, score: float) -> str:
        """Interpret relevance score."""
        if score >= 0.8:
            return "✅ EXCELLENT - Directly addresses query"
        elif score >= 0.6:
            return "✓ GOOD - Mostly relevant"
        elif score >= 0.4:
            return "⚠ FAIR - Partially addresses query"
        else:
            return "❌ POOR - Off-topic answer"
    
    def _interpret_correctness(self, score: float) -> str:
        """Interpret correctness score."""
        if score >= 0.9:
            return "✅ EXCELLENT - Matches ground truth closely"
        elif score >= 0.7:
            return "✓ GOOD - Minor differences from ground truth"
        elif score >= 0.5:
            return "⚠ FAIR - Partially correct"
        else:
            return "❌ POOR - Incorrect answer"
    
    def generate_report(self) -> str:
        """Generate a human-readable evaluation report."""
        if not self.results:
            return "No results to report"
        
        report = "=" * 60 + "\n"
        report += "GENERATION EVALUATION REPORT\n"
        report += "=" * 60 + "\n\n"
        
        report += f"Total Answers Evaluated: {len(self.results)}\n\n"
        
        # Average scores
        avg_faithfulness = sum(r['faithfulness'] for r in self.results) / len(self.results)
        avg_relevance = sum(r['relevance'] for r in self.results) / len(self.results)
        
        report += "AVERAGE SCORES:\n"
        report += "-" * 60 + "\n"
        report += f"  Faithfulness: {avg_faithfulness:.4f} ({avg_faithfulness*100:.2f}%)\n"
        report += f"  Relevance:    {avg_relevance:.4f} ({avg_relevance*100:.2f}%)\n"
        
        if any('correctness' in r for r in self.results):
            correctness_results = [r['correctness'] for r in self.results if 'correctness' in r]
            avg_correctness = sum(correctness_results) / len(correctness_results)
            report += f"  Correctness:  {avg_correctness:.4f} ({avg_correctness*100:.2f}%)\n"
        
        report += "\n" + "=" * 60 + "\n"
        
        return report
