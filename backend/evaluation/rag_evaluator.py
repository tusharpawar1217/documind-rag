"""
RAG System Evaluator
End-to-end evaluation of the RAG pipeline.
"""

from typing import List, Dict, Optional
import time
from datetime import datetime
from .retrieval_metrics import RetrievalEvaluator
from .generation_metrics import GenerationEvaluator
from .test_data_generator import TestDataGenerator


class RAGEvaluator:
    """
    End-to-end RAG evaluation.
    Combines retrieval and generation metrics.
    """
    
    def __init__(self):
        self.retrieval_eval = RetrievalEvaluator()
        self.generation_eval = GenerationEvaluator()
        self.test_generator = TestDataGenerator()
        
        self.eval_results = {
            'timestamp': None,
            'total_queries': 0,
            'retrieval_metrics': {},
            'generation_metrics': {},
            'latency_metrics': {},
            'errors': []
        }
    
    def evaluate_retrieval(
        self,
        retrieval_function,
        test_queries: List[Dict],
        k_values: List[int] = [1, 3, 5, 10]
    ) -> Dict:
        """
        Evaluate retrieval performance.
        
        Args:
            retrieval_function: Function that takes query and returns list of chunk IDs
            test_queries: List of test queries with ground truth
            k_values: K values for metrics
            
        Returns:
            Evaluation results
        """
        print("🔍 Evaluating Retrieval...")
        print("=" * 60)
        
        for i, test in enumerate(test_queries, 1):
            query = test['query']
            relevant = test.get('relevant_chunks', set())
            
            if not relevant:
                continue
            
            try:
                # Measure retrieval latency
                start_time = time.time()
                retrieved = retrieval_function(query)
                latency = time.time() - start_time
                
                # Evaluate
                results = self.retrieval_eval.evaluate_query(
                    query, retrieved, relevant, k_values
                )
                
                print(f"  [{i}/{len(test_queries)}] {query[:50]}...")
                print(f"    Recall@5: {results['recall@5']:.3f} | "
                      f"Precision@5: {results['precision@5']:.3f} | "
                      f"MRR: {results['mrr']:.3f} | "
                      f"Latency: {latency*1000:.0f}ms")
                
            except Exception as e:
                self.eval_results['errors'].append({
                    'query': query,
                    'error': str(e),
                    'type': 'retrieval'
                })
                print(f"    ❌ ERROR: {str(e)}")
        
        # Aggregate results
        aggregated = self.retrieval_eval.aggregate_results()
        self.eval_results['retrieval_metrics'] = aggregated
        
        print("\n" + self.retrieval_eval.generate_report())
        return aggregated
    
    def evaluate_generation(
        self,
        generation_function,
        test_cases: List[Dict]
    ) -> Dict:
        """
        Evaluate generation quality.
        
        Args:
            generation_function: Function that takes (query, context) and returns answer
            test_cases: List of test cases with query, context, ground_truth
            
        Returns:
            Evaluation results
        """
        print("\n🤖 Evaluating Generation...")
        print("=" * 60)
        
        for i, test in enumerate(test_cases, 1):
            query = test['query']
            context = test['context']
            ground_truth = test.get('ground_truth')
            
            try:
                # Measure generation latency
                start_time = time.time()
                answer = generation_function(query, context)
                latency = time.time() - start_time
                
                # Evaluate
                results = self.generation_eval.evaluate_answer(
                    query, answer, context, ground_truth
                )
                
                print(f"  [{i}/{len(test_cases)}] {query[:50]}...")
                print(f"    Faithfulness: {results['faithfulness']:.3f} | "
                      f"Relevance: {results['relevance']:.3f} | "
                      f"Latency: {latency*1000:.0f}ms")
                
                if 'correctness' in results:
                    print(f"    Correctness: {results['correctness']:.3f}")
                
            except Exception as e:
                self.eval_results['errors'].append({
                    'query': query,
                    'error': str(e),
                    'type': 'generation'
                })
                print(f"    ❌ ERROR: {str(e)}")
        
        print("\n" + self.generation_eval.generate_report())
        return self.generation_eval.results
    
    def evaluate_end_to_end(
        self,
        rag_function,
        test_queries: List[Dict]
    ) -> Dict:
        """
        Evaluate complete RAG pipeline.
        
        Args:
            rag_function: Function that takes query and returns full response
            test_queries: List of test queries
            
        Returns:
            Complete evaluation results
        """
        print("\n🚀 Evaluating End-to-End RAG Pipeline...")
        print("=" * 60)
        
        latencies = []
        
        for i, test in enumerate(test_queries, 1):
            query = test['query']
            
            try:
                # Measure full pipeline latency
                start_time = time.time()
                response = rag_function(query)
                latency = time.time() - start_time
                latencies.append(latency)
                
                print(f"  [{i}/{len(test_queries)}] {query[:50]}...")
                print(f"    Latency: {latency*1000:.0f}ms | "
                      f"Results: {response.get('total_results', 0)}")
                
            except Exception as e:
                self.eval_results['errors'].append({
                    'query': query,
                    'error': str(e),
                    'type': 'end-to-end'
                })
                print(f"    ❌ ERROR: {str(e)}")
        
        # Calculate latency statistics
        if latencies:
            self.eval_results['latency_metrics'] = {
                'mean': sum(latencies) / len(latencies),
                'min': min(latencies),
                'max': max(latencies),
                'p50': sorted(latencies)[len(latencies)//2],
                'p95': sorted(latencies)[int(len(latencies)*0.95)],
                'p99': sorted(latencies)[int(len(latencies)*0.99)]
            }
        
        return self.eval_results
    
    def generate_comprehensive_report(self) -> str:
        """Generate a complete evaluation report."""
        self.eval_results['timestamp'] = datetime.now().isoformat()
        
        report = "\n" + "=" * 80 + "\n"
        report += "RAG SYSTEM EVALUATION REPORT\n"
        report += "=" * 80 + "\n\n"
        
        report += f"Timestamp: {self.eval_results['timestamp']}\n"
        report += f"Total Queries: {len(self.retrieval_eval.results)}\n"
        report += f"Errors: {len(self.eval_results['errors'])}\n\n"
        
        # Retrieval metrics
        if self.retrieval_eval.results:
            report += self.retrieval_eval.generate_report()
            report += "\n"
        
        # Generation metrics
        if self.generation_eval.results:
            report += self.generation_eval.generate_report()
            report += "\n"
        
        # Latency metrics
        if self.eval_results['latency_metrics']:
            latency = self.eval_results['latency_metrics']
            report += "LATENCY METRICS\n"
            report += "=" * 80 + "\n"
            report += f"  Mean:    {latency['mean']*1000:.0f}ms\n"
            report += f"  Median:  {latency['p50']*1000:.0f}ms\n"
            report += f"  P95:     {latency['p95']*1000:.0f}ms\n"
            report += f"  P99:     {latency['p99']*1000:.0f}ms\n"
            report += f"  Min:     {latency['min']*1000:.0f}ms\n"
            report += f"  Max:     {latency['max']*1000:.0f}ms\n\n"
        
        # Errors
        if self.eval_results['errors']:
            report += "ERRORS\n"
            report += "=" * 80 + "\n"
            for error in self.eval_results['errors']:
                report += f"  Query: {error['query']}\n"
                report += f"  Type: {error['type']}\n"
                report += f"  Error: {error['error']}\n\n"
        
        # Overall assessment
        report += "OVERALL ASSESSMENT\n"
        report += "=" * 80 + "\n"
        
        if self.eval_results['retrieval_metrics']:
            recall = self.eval_results['retrieval_metrics'].get('recall@5', 0)
            precision = self.eval_results['retrieval_metrics'].get('precision@5', 0)
            
            report += f"  Retrieval: "
            if recall >= 0.7 and precision >= 0.7:
                report += "✅ EXCELLENT\n"
            elif recall >= 0.5 and precision >= 0.5:
                report += "✓ GOOD\n"
            else:
                report += "⚠ NEEDS IMPROVEMENT\n"
        
        if self.generation_eval.results:
            avg_faithfulness = sum(r['faithfulness'] for r in self.generation_eval.results) / len(self.generation_eval.results)
            avg_relevance = sum(r['relevance'] for r in self.generation_eval.results) / len(self.generation_eval.results)
            
            report += f"  Generation: "
            if avg_faithfulness >= 0.8 and avg_relevance >= 0.8:
                report += "✅ EXCELLENT\n"
            elif avg_faithfulness >= 0.6 and avg_relevance >= 0.6:
                report += "✓ GOOD\n"
            else:
                report += "⚠ NEEDS IMPROVEMENT\n"
        
        if self.eval_results['latency_metrics']:
            p95 = self.eval_results['latency_metrics']['p95']
            report += f"  Latency: "
            if p95 < 1.0:
                report += "✅ EXCELLENT (<1s)\n"
            elif p95 < 3.0:
                report += "✓ GOOD (<3s)\n"
            else:
                report += "⚠ SLOW (>3s)\n"
        
        report += "\n" + "=" * 80 + "\n"
        
        return report
    
    def save_report(self, filename: str = "evaluation_report.txt"):
        """Save evaluation report to file."""
        report = self.generate_comprehensive_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 Report saved to: {filename}")
