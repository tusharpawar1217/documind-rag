"""
Validate Backend Structure

This script validates that all required RAG components are present and importable.
"""

import sys
from pathlib import Path

def validate_structure():
    """Validate backend structure."""
    
    print("=" * 60)
    print("BACKEND STRUCTURE VALIDATION")
    print("=" * 60)
    
    errors = []
    warnings = []
    
    # Check main files
    required_files = [
        "config.yaml",
        "main.py",
        "requirements.txt",
    ]
    
    print("\n1. Checking main files...")
    for file in required_files:
        if Path(file).exists():
            print(f"   ✓ {file}")
        else:
            errors.append(f"Missing: {file}")
            print(f"   ✗ {file}")
    
    # Check src directory structure
    print("\n2. Checking src/ directory structure...")
    required_modules = {
        "ingestion": ["__init__.py", "loader.py"],
        "chunking": ["__init__.py", "chunker.py"],
        "embeddings": ["__init__.py", "embedder.py"],
        "vectordb": ["__init__.py", "vector_store.py"],
        "retrieval": ["__init__.py", "retriever.py"],
        "prompts": ["__init__.py", "prompt_templates.py"],
        "llm": ["__init__.py", "llm_client.py"],
        "api": ["__init__.py", "routes.py"],
        "utils": ["__init__.py", "helpers.py"],
    }
    
    src_path = Path("src")
    if not src_path.exists():
        errors.append("Missing: src/ directory")
        print("   ✗ src/ directory not found")
    else:
        for module, files in required_modules.items():
            module_path = src_path / module
            if module_path.exists():
                print(f"   ✓ src/{module}/")
                for file in files:
                    file_path = module_path / file
                    if file_path.exists():
                        print(f"      ✓ {file}")
                    else:
                        errors.append(f"Missing: src/{module}/{file}")
                        print(f"      ✗ {file}")
            else:
                errors.append(f"Missing: src/{module}/")
                print(f"   ✗ src/{module}/")
    
    # Check data directories
    print("\n3. Checking data directories...")
    data_dirs = ["data/uploads", "data/vectors", "logs"]
    for dir_path in data_dirs:
        if Path(dir_path).exists():
            print(f"   ✓ {dir_path}/")
        else:
            warnings.append(f"Missing: {dir_path}/ (will be created at runtime)")
            print(f"   ⚠ {dir_path}/ (will be created)")
    
    # Check old app/ directory
    print("\n4. Checking legacy app/ directory...")
    app_path = Path("app")
    if app_path.exists():
        print(f"   ✓ app/ (legacy code preserved)")
    else:
        warnings.append("app/ directory not found (legacy code)")
        print(f"   ⚠ app/ not found")
    
    # Test imports
    print("\n5. Testing module imports...")
    try:
        sys.path.insert(0, str(Path.cwd()))
        
        test_imports = [
            ("src.ingestion.loader", "document_loader"),
            ("src.chunking.chunker", "text_chunker"),
            ("src.embeddings.embedder", "embedder"),
            ("src.vectordb.vector_store", "vector_store"),
            ("src.retrieval.retriever", "Retriever"),
            ("src.prompts.prompt_templates", "prompts"),
            ("src.llm.llm_client", "llm_client"),
            ("src.api.routes", "app"),
            ("src.utils.helpers", "load_config"),
        ]
        
        for module_name, object_name in test_imports:
            try:
                module = __import__(module_name, fromlist=[object_name])
                if hasattr(module, object_name):
                    print(f"   ✓ {module_name}.{object_name}")
                else:
                    errors.append(f"Import error: {module_name}.{object_name} not found")
                    print(f"   ✗ {module_name}.{object_name}")
            except Exception as e:
                errors.append(f"Import error: {module_name} - {str(e)}")
                print(f"   ✗ {module_name} - {str(e)}")
    
    except Exception as e:
        errors.append(f"Import test failed: {str(e)}")
        print(f"   ✗ Import test failed: {str(e)}")
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    if not errors and not warnings:
        print("✓ ALL CHECKS PASSED! Structure is valid.")
        return 0
    else:
        if warnings:
            print(f"\n⚠ WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"   - {warning}")
        
        if errors:
            print(f"\n✗ ERRORS ({len(errors)}):")
            for error in errors:
                print(f"   - {error}")
            print("\nPlease fix the errors above.")
            return 1
        else:
            print("\n✓ Structure is valid (with warnings).")
            return 0


if __name__ == "__main__":
    exit_code = validate_structure()
    sys.exit(exit_code)
