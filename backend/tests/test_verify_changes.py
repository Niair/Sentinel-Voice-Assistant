"""
Verification script to check if all files have been updated correctly.

Run this to verify your changes before testing the application.
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def check_file_signatures():
    """Check key indicators in each file to verify they're the fixed versions."""
    
    print("=" * 70)
    print("🔍 VERIFYING FILE UPDATES")
    print("=" * 70)
    print()
    
    all_correct = True
    
    # 1. Check models.py (should be Pydantic-only, no SQLAlchemy)
    print("1. Checking models.py...")
    try:
        with open('app/models.py', 'r') as f:
            content = f.read()
            
        has_sqlalchemy = 'from sqlalchemy' in content
        has_base = 'class MonitoringJob(Base)' in content or 'class MonitoringEvent(Base)' in content
        
        if has_sqlalchemy or has_base:
            print("   ❌ WRONG: models.py still has SQLAlchemy code")
            print("      → Need to replace with Pydantic-only version")
            all_correct = False
        else:
            print("   ✅ CORRECT: models.py is Pydantic-only")
    except Exception as e:
        print(f"   ⚠️  ERROR reading models.py: {e}")
        all_correct = False
    
    # 2. Check database.py (should NOT import from models.py at module level)
    print("\n2. Checking database.py...")
    try:
        with open('app/database.py', 'r') as f:
            content = f.read()
        
        has_models_import = 'from app.models import' in content and 'def init_db' not in content[:content.find('from app.models import')]
        has_local_import = 'from app.db_models import MonitoringJob' in content
        
        if has_models_import:
            print("   ❌ WRONG: database.py imports from models.py at module level")
            print("      → This causes circular import")
            all_correct = False
        elif has_local_import:
            print("   ✅ CORRECT: database.py has local imports in init_db()")
        else:
            print("   ⚠️  WARNING: Couldn't verify database.py structure")
    except Exception as e:
        print(f"   ⚠️  ERROR reading database.py: {e}")
        all_correct = False
    
    # 3. Check events.py (should have proper async generator)
    print("\n3. Checking events.py...")
    try:
        with open('app/events.py', 'r') as f:
            content = f.read()
        
        has_while_true = 'while True:' in content and 'yield' in content
        has_broken_return = 'return await _event_queue.get()' in content
        
        if has_broken_return:
            print("   ❌ WRONG: events.py has broken 'return await' pattern")
            print("      → Should use 'while True: yield'")
            all_correct = False
        elif has_while_true:
            print("   ✅ CORRECT: events.py has proper async generator")
        else:
            print("   ⚠️  WARNING: Couldn't verify events.py structure")
    except Exception as e:
        print(f"   ⚠️  ERROR reading events.py: {e}")
        all_correct = False
    
    # 4. Check alert_store.py (should be async)
    print("\n4. Checking alert_store.py...")
    try:
        with open('app/alert_store.py', 'r') as f:
            content = f.read()
        
        has_async_save = 'async def save_alert(' in content
        
        if not has_async_save:
            print("   ❌ WRONG: alert_store.py save_alert() is not async")
            all_correct = False
        else:
            print("   ✅ CORRECT: alert_store.py has async save_alert()")
    except Exception as e:
        print(f"   ⚠️  ERROR reading alert_store.py: {e}")
        all_correct = False
    
    # 5. Check alert_processor.py (should have single start() method)
    print("\n5. Checking alert_processor.py...")
    try:
        with open('app/alert_processor.py', 'r') as f:
            content = f.read()
        
        start_count = content.count('async def start(')
        
        if start_count > 1:
            print(f"   ❌ WRONG: alert_processor.py has {start_count} start() methods")
            print("      → Should have only 1")
            all_correct = False
        elif start_count == 1:
            print("   ✅ CORRECT: alert_processor.py has single start() method")
        else:
            print("   ⚠️  WARNING: No start() method found")
            all_correct = False
    except Exception as e:
        print(f"   ⚠️  ERROR reading alert_processor.py: {e}")
        all_correct = False
    
    # 6. Check monitoring_worker.py (should import Severity correctly)
    print("\n6. Checking monitoring_worker.py...")
    try:
        with open('app/monitoring_worker.py', 'r') as f:
            content = f.read()
        
        has_severity_import = 'from app.models import' in content and 'Severity' in content
        uses_severity = 'severity=Severity.' in content
        
        if not has_severity_import:
            print("   ❌ WRONG: monitoring_worker.py doesn't import Severity")
            all_correct = False
        elif not uses_severity:
            print("   ⚠️  WARNING: Severity imported but not used correctly")
        else:
            print("   ✅ CORRECT: monitoring_worker.py imports and uses Severity")
    except Exception as e:
        print(f"   ⚠️  ERROR reading monitoring_worker.py: {e}")
        all_correct = False
    
    # Final result
    print("\n" + "=" * 70)
    if all_correct:
        print("✅ ALL FILES VERIFIED - Ready to test!")
        print("=" * 70)
        print("\nNext step: Run the application")
        print("  uv run python -m app.main")
        return 0
    else:
        print("❌ SOME FILES NEED UPDATES")
        print("=" * 70)
        print("\nPlease replace the incorrect files with the fixed versions.")
        print("See the outputs directory for correct versions.")
        return 1


if __name__ == "__main__":
    sys.exit(check_file_signatures())