"""
Run RAG System Evaluation

Execute this script to evaluate your RAG system.
Usage: python run_evaluation.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from evaluation.rag_evaluator import RAGEvaluator
from evaluation.test_data_generator import TestDataGenerator
import requests
import json


# Configuration
API_BASE_URL = "http://localhost:8000"


def fetch_chunks_from_api():
    """Fetch all document chunks from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/documents")
        documents = response.json().get('documents', [])
        
        # In a real scenario, you'd have an endpoint to get chunks
        # For now, return empty list
        return []
    except Exception as e:
        print(f"Warning: Could not fetch chunks - {e}")
        return []


def retrieval_function(query: str, top_k: int = 5) -> list:
    """
    Wrapper for retrieval API call.
    Returns list of chunk IDs.
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search/query",
            json={"query": query, "top_k": top_k},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            # Extract chunk IDs from metadata
            return [r['metadata']['chunk_index'] for r in results if 'metadata' in r]
        else:
            print(f"Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"Retrieval error: {e}")
        return []


def generation_function(query: str, context: str) -> str:
    """
    Wrapper for generation.
    Returns generated answer.
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search/query",
            json={
                "query": query,
                "top_k": 5,
                "generate_response": True
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('response', '')
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Generation error: {e}"


def rag_function(query: str) -> dict:
    """
    Full RAG pipeline.
    Returns complete response.
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search/query",
            json={"query": query, "top_k": 5},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.status_code, "total_results": 0}
    except Exception as e:
        return {"error": str(e), "total_results": 0}


def run_quick_evaluation():
    """Run a quick evaluation with default queries."""
    print("\n" + "=" * 80)
    print("DOCUMIND RAG - QUICK EVALUATION")
    print("=" * 80 + "\n")
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code != 200:
            print("❌ Error: Backend API is not responding")
            print(f"   Make sure the server is running at {API_BASE_URL}")
            return
        print("✅ Backend API is running\n")
    except Exception as e:
        print(f"❌ Error: Cannot connect to backend at {API_BASE_URL}")
        print(f"   {str(e)}")
        print("\n   Start the backend first:")
        print("   python backend/test_server.py")
        return
    
    # Initialize evaluator
    evaluator = RAGEvaluator()
    test_gen = TestDataGenerator()
    
    # Load test queries
    test_queries = test_gen.load_default_test_queries()
    
    print(f"📊 Running evaluation with {len(test_queries)} test queries...\n")
    
    # Evaluate end-to-end
    evaluator.evaluate_end_to_end(rag_function, test_queries)
    
    # Generate and display report
    report = evaluator.generate_comprehensive_report()
    print(report)
    
    # Save report
    evaluator.save_report("evaluation_report.txt")
    
    print("\n✅ Evaluation complete!")
    print("\nNext steps:")
    print("  1. Review evaluation_report.txt for detailed metrics")
    print("  2. Upload a PDF and run evaluation again")
    print("  3. Compare metrics before/after changes")


def run_full_evaluation_with_ground_truth():
    """
    Run full evaluation with manually labeled ground truth.
    Create your own test set here.
    """
    print("\n" + "=" * 80)
    print("DOCUMIND RAG - FULL EVALUATION WITH GROUND TRUTH")
    print("=" * 80 + "\n")
    
    # Check API
    try:
        requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        print("✅ Backend API is running\n")
    except Exception as e:
        print(f"❌ Error: Cannot connect to backend at {API_BASE_URL}")
        return
    
    evaluator = RAGEvaluator()
    
    # Example: Manually labeled test set
    # Replace this with your actual labeled data
    labeled_test_set = [
        {
            'query': 'What is the research methodology?',
            'relevant_chunks': {0, 1, 2},  # Chunk IDs that should be retrieved
            'context': 'The research methodology employed...',  # Expected context
            'ground_truth': 'The research used a mixed-methods approach...'  # Expected answer
        },
        # Add more labeled examples here
    ]
    
    if not labeled_test_set or labeled_test_set[0]['query'] == 'What is the research methodology?':
        print("⚠️  No labeled test set provided.")
        print("   Edit run_evaluation.py and add your labeled test cases")
        print("   in the 'labeled_test_set' variable.\n")
        print("   Each test case should have:")
        print("     - query: The search query")
        print("     - relevant_chunks: Set of chunk IDs that should be retrieved")
        print("     - context: Expected context text")
        print("     - ground_truth: Expected answer\n")
        return
    
    print(f"📊 Running evaluation with {len(labeled_test_set)} labeled queries...\n")
    
    # Evaluate retrieval
    print("\n1️⃣  RETRIEVAL EVALUATION")
    print("-" * 80)
    evaluator.evaluate_retrieval(retrieval_function, labeled_test_set)
    
    # Evaluate generation
    print("\n2️⃣  GENERATION EVALUATION")
    print("-" * 80)
    evaluator.evaluate_generation(generation_function, labeled_test_set)
    
    # Generate report
    report = evaluator.generate_comprehensive_report()
    print(report)
    
    # Save report
    evaluator.save_report("full_evaluation_report.txt")
    
    print("\n✅ Full evaluation complete!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate RAG System')
    parser.add_argument(
        '--mode',
        choices=['quick', 'full'],
        default='quick',
        help='Evaluation mode: quick (no ground truth) or full (with ground truth)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'quick':
        run_quick_evaluation()
    else:
        run_full_evaluation_with_ground_truth()
