"""
Pre-flight Check for Step 2 Qdrant RAG
Run this before running the comprehensive tests

Usage: python tests/preflight_check.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_env_vars():
    """Check required environment variables"""
    print("=" * 70)
    print("1. Environment Variables Check")
    print("=" * 70)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        'QDRANT_URL': os.getenv('QDRANT_URL'),
        'QDRANT_API_KEY': os.getenv('QDRANT_API_KEY'),
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            # Show only first 30 chars for security
            display_value = var_value[:30] + "..." if len(var_value) > 30 else var_value
            if 'KEY' in var_name:
                display_value = "***SET***"
            print(f"✅ {var_name}: {display_value}")
        else:
            print(f"❌ {var_name}: NOT SET")
            all_set = False
    
    return all_set


def check_imports():
    """Check required Python packages"""
    print("\n" + "=" * 70)
    print("2. Python Packages Check")
    print("=" * 70)
    
    imports_to_check = [
        ('qdrant_client', 'qdrant-client'),
        ('langchain_google_genai', 'langchain-google-genai'),
        ('langchain_core.documents', 'langchain-core'),
        ('langchain_community.document_loaders', 'langchain-community'),
    ]
    
    all_ok = True
    for module_name, package_name in imports_to_check:
        try:
            __import__(module_name)
            if module_name == 'qdrant_client':
                try:
                    import qdrant_client
                    # Try to get version, but don't fail if not available
                    version = getattr(qdrant_client, '__version__', 'installed')
                    print(f"✅ {package_name}: {version}")
                except:
                    print(f"✅ {package_name}: installed")
            else:
                print(f"✅ {package_name}: installed")
        except ImportError as e:
            print(f"❌ {package_name}: NOT INSTALLED")
            print(f"   Install with: uv pip install {package_name}")
            all_ok = False
    
    return all_ok


def check_files():
    """Check for FAISS artifacts"""
    print("\n" + "=" * 70)
    print("3. Clean Workspace Check")
    print("=" * 70)
    
    uploads_dir = Path(__file__).parent.parent / "uploads"
    
    if not uploads_dir.exists():
        print("✅ uploads/ directory doesn't exist yet (will be created on first upload)")
        return True
    
    faiss_files = list(uploads_dir.glob("*.faiss")) + list(uploads_dir.glob("*.pkl"))
    
    if faiss_files:
        print(f"⚠️ Found {len(faiss_files)} FAISS artifact(s):")
        for f in faiss_files:
            print(f"   - {f.name}")
        print("\n   This means previous FAISS-based RAG was used.")
        print("   These should be deleted before testing Qdrant:")
        print(f"   rm -f {uploads_dir}/*.faiss {uploads_dir}/*.pkl")
        return False
    else:
        pdf_count = len(list(uploads_dir.glob("*.pdf")))
        print(f"✅ No FAISS artifacts found")
        print(f"   Found {pdf_count} PDF file(s) (this is OK)")
        return True


def check_code_setup():
    """Check if graph.py and main.py are using Qdrant"""
    print("\n" + "=" * 70)
    print("4. Code Configuration Check")
    print("=" * 70)
    
    graph_py = Path(__file__).parent.parent / "app" / "graph.py"
    main_py = Path(__file__).parent.parent / "app" / "main.py"
    
    all_ok = True
    
    # Check graph.py
    if not graph_py.exists():
        print("❌ graph.py not found")
        return False
    
    with open(graph_py, 'r', encoding='utf-8') as f:
        graph_content = f.read()
    
    # Check for Qdrant import
    if 'from app.qdrant_manager import get_qdrant_client' in graph_content:
        print("✅ graph.py: Qdrant client imported")
    else:
        print("❌ graph.py: Missing Qdrant client import")
        all_ok = False
    
    # Check for async rag_tool
    if 'async def rag_tool' in graph_content:
        print("✅ graph.py: rag_tool is async")
    else:
        print("⚠️ graph.py: rag_tool might not be async")
        all_ok = False
    
    # Check for async process_document
    if 'async def process_document' in graph_content:
        print("✅ graph.py: process_document is async")
    else:
        print("⚠️ graph.py: process_document might not be async")
        all_ok = False
    
    # Check for FAISS imports (should be commented out or removed)
    if 'from langchain_postgres import PGVector' in graph_content and \
       '# from langchain_postgres import PGVector' not in graph_content:
        print("⚠️ graph.py: PGVector import is active (should be commented out)")
        all_ok = False
    else:
        print("✅ graph.py: No active PGVector import")
    
    # Check main.py
    if not main_py.exists():
        print("❌ main.py not found")
        return False
    
    with open(main_py, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    # Check for async document processing
    if 'await process_document' in main_content:
        print("✅ main.py: Using await for process_document")
    else:
        print("⚠️ main.py: process_document calls might not be awaited")
        all_ok = False
    
    return all_ok


def main():
    print("\n" + "🔍" * 35)
    print("STEP 2: PRE-FLIGHT CHECK")
    print("🔍" * 35 + "\n")
    
    results = []
    results.append(("Environment Variables", check_env_vars()))
    results.append(("Python Packages", check_imports()))
    results.append(("Clean Workspace", check_files()))
    results.append(("Code Configuration", check_code_setup()))
    
    # Summary
    print("\n" + "=" * 70)
    print("PRE-FLIGHT CHECK SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for check_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    
    if all_passed:
        print("🎉 All pre-flight checks passed!")
        print("\nYou're ready to run the comprehensive test suite:")
        print("   python tests/test_qdrant_comprehensive.py")
        return True
    else:
        print("⚠️ Some checks failed. Please fix the issues above before testing.")
        print("\nCommon fixes:")
        print("1. Add missing environment variables to backend/.env")
        print("2. Install missing packages: uv pip install <package-name>")
        print("3. Delete FAISS artifacts: rm -f uploads/*.faiss uploads/*.pkl")
        print("4. Update graph.py and main.py with Qdrant code")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)