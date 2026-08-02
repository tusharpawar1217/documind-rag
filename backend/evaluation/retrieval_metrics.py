"""
Retrieval Evaluation Metrics
Measures how well the retrieval system finds relevant documents.
"""

from typing import List, Dict, Set, Tuple
import numpy as np
from collections import defaultdict


class RetrievalEvaluator:
    """Evaluates retrieval quality using standard IR metrics."""
    
    def __init__(self):
        self.results = []
    
    def recall_at_k(self, retrieved: List[str], relevant: Set[str], k: int = 5) -> float:
        """
        Recall@k - Of all relevant chunks, how many appear in top-k?
        Most important for RAG since generation can't use what wasn't retrieved.
        
        Args:
            retrieved: List of retrieved chunk IDs (ordered by relevance)
            relevant: Set of ground truth relevant chunk IDs
            k: Number of top results to consider
            
        Returns:
            Recall score (0-1)
        """
        if not relevant:
            return 0.0
        
        top_k = set(retrieved[:k])
        hits = top_k.intersection(relevant)
        return len(hits) / len(relevant)
    
    def precision_at_k(self, retrieved: List[str], relevant: Set[str], k: int = 5) -> float:
        """
        Precision@k - Of top-k retrieved, how many are relevant?
        Matters because noisy context degrades LLM answers.
        
        Args:
            retrieved: List of retrieved chunk IDs (ordered by relevance)
            relevant: Set of ground truth relevant chunk IDs
            k: Number of top results to consider
            
        Returns:
            Precision score (0-1)
        """
        if k == 0:
            return 0.0
        
        top_k = set(retrieved[:k])
        hits = top_k.intersection(relevant)
        return len(hits) / k
    
    def mean_reciprocal_rank(self, retrieved: List[str], relevant: Set[str]) -> float:
        """
        MRR - How high does the first relevant chunk rank?
        Good for "is the best answer near the top?"
        
        Args:
            retrieved: List of retrieved chunk IDs (ordered by relevance)
            relevant: Set of ground truth relevant chunk IDs
            
        Returns:
            Reciprocal rank of first relevant item (0-1)
        """
        for i, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant:
                return 1.0 / i
        return 0.0
    
    def average_precision(self, retrieved: List[str], relevant: Set[str]) -> float:
        """
        Average Precision - Average of precision values at each relevant position.
        
        Args:
            retrieved: List of retrieved chunk IDs
            relevant: Set of ground truth relevant chunk IDs
            
        Returns:
            Average precision score (0-1)
        """
        if not relevant:
            return 0.0
        
        precisions = []
        hits = 0
        
        for i, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant:
                hits += 1
                precisions.append(hits / i)
        
        return sum(precisions) / len(relevant) if precisions else 0.0
    
    def ndcg_at_k(self, retrieved: List[str], relevant_scores: Dict[str, float], k: int = 5) -> float:
        """
        nDCG@k - Normalized Discounted Cumulative Gain
        For graded relevance (not just binary).
        
        Args:
            retrieved: List of retrieved chunk IDs (ordered by relevance)
            relevant_scores: Dict mapping chunk IDs to relevance scores (0-3)
            k: Number of top results to consider
            
        Returns:
            nDCG score (0-1)
        """
        def dcg(scores: List[float]) -> float:
            return sum(score / np.log2(i + 2) for i, score in enumerate(scores))
        
        # Get relevance scores for retrieved items
        retrieved_scores = [relevant_scores.get(doc_id, 0.0) for doc_id in retrieved[:k]]
        
        # Ideal ranking (sorted by relevance)
        ideal_scores = sorted(relevant_scores.values(), reverse=True)[:k]
        
        dcg_score = dcg(retrieved_scores)
        idcg_score = dcg(ideal_scores)
        
        return dcg_score / idcg_score if idcg_score > 0 else 0.0
    
    def evaluate_query(
        self,
        query: str,
        retrieved: List[str],
        relevant: Set[str],
        k_values: List[int] = [1, 3, 5, 10]
    ) -> Dict[str, float]:
        """
        Evaluate a single query across all metrics.
        
        Args:
            query: The search query
            retrieved: List of retrieved chunk IDs
            relevant: Set of ground truth relevant chunk IDs
            k_values: List of k values to evaluate
            
        Returns:
            Dictionary of metric scores
        """
        results = {
            'query': query,
            'num_relevant': len(relevant),
            'num_retrieved': len(retrieved)
        }
        
        # Calculate metrics for each k
        for k in k_values:
            results[f'recall@{k}'] = self.recall_at_k(retrieved, relevant, k)
            results[f'precision@{k}'] = self.precision_at_k(retrieved, relevant, k)
        
        # Overall metrics
        results['mrr'] = self.mean_reciprocal_rank(retrieved, relevant)
        results['map'] = self.average_precision(retrieved, relevant)
        
        self.results.append(results)
        return results
    
    def aggregate_results(self) -> Dict[str, float]:
        """
        Aggregate metrics across all evaluated queries.
        
        Returns:
            Dictionary of averaged metrics
        """
        if not self.results:
            return {}
        
        aggregated = defaultdict(list)
        
        for result in self.results:
            for key, value in result.items():
                if isinstance(value, (int, float)) and key not in ['num_relevant', 'num_retrieved']:
                    aggregated[key].append(value)
        
        return {
            key: np.mean(values) for key, values in aggregated.items()
        }
    
    def generate_report(self) -> str:
        """Generate a human-readable evaluation report."""
        agg = self.aggregate_results()
        
        report = "=" * 60 + "\n"
        report += "RETRIEVAL EVALUATION REPORT\n"
        report += "=" * 60 + "\n\n"
        
        report += f"Total Queries Evaluated: {len(self.results)}\n\n"
        
        # Recall metrics
        report += "RECALL (Coverage - Did we find relevant chunks?)\n"
        report += "-" * 60 + "\n"
        for k in [1, 3, 5, 10]:
            if f'recall@{k}' in agg:
                score = agg[f'recall@{k}']
                report += f"  Recall@{k:2d}: {score:.4f} ({score*100:.2f}%)\n"
        
        # Precision metrics
        report += "\nPRECISION (Quality - Are retrieved chunks relevant?)\n"
        report += "-" * 60 + "\n"
        for k in [1, 3, 5, 10]:
            if f'precision@{k}' in agg:
                score = agg[f'precision@{k}']
                report += f"  Precision@{k:2d}: {score:.4f} ({score*100:.2f}%)\n"
        
        # Ranking metrics
        report += "\nRANKING (Is best answer near the top?)\n"
        report += "-" * 60 + "\n"
        if 'mrr' in agg:
            report += f"  MRR:  {agg['mrr']:.4f} (Mean Reciprocal Rank)\n"
        if 'map' in agg:
            report += f"  MAP:  {agg['map']:.4f} (Mean Average Precision)\n"
        
        report += "\n" + "=" * 60 + "\n"
        
        # Interpretation
        report += "\nINTERPRETATION:\n"
        if 'recall@5' in agg:
            recall = agg['recall@5']
            if recall >= 0.8:
                report += "  ✅ EXCELLENT recall - finding most relevant chunks\n"
            elif recall >= 0.6:
                report += "  ✓ GOOD recall - finding many relevant chunks\n"
            elif recall >= 0.4:
                report += "  ⚠ FAIR recall - missing some relevant chunks\n"
            else:
                report += "  ❌ POOR recall - missing many relevant chunks\n"
        
        if 'precision@5' in agg:
            precision = agg['precision@5']
            if precision >= 0.8:
                report += "  ✅ EXCELLENT precision - low noise\n"
            elif precision >= 0.6:
                report += "  ✓ GOOD precision - acceptable noise\n"
            elif precision >= 0.4:
                report += "  ⚠ FAIR precision - noisy results may degrade answers\n"
            else:
                report += "  ❌ POOR precision - too much noise\n"
        
        if 'mrr' in agg:
            mrr = agg['mrr']
            if mrr >= 0.8:
                report += "  ✅ EXCELLENT ranking - best answer usually at top\n"
            elif mrr >= 0.6:
                report += "  ✓ GOOD ranking - best answer usually in top 3\n"
            else:
                report += "  ⚠ FAIR ranking - best answer often not at top\n"
        
        report += "\n" + "=" * 60 + "\n"
        
        return report
