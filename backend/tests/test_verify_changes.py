"""
Verification script with UTF-8 encoding support.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def check_file_signatures():
    """Check key indicators in each file to verify they're the fixed versions."""
    
    print("=" * 70)
    print("🔍 VERIFYING FILE UPDATES")
    print("=" * 70)
    print()
    
    all_correct = True
    
    # 1. Check models.py
    print("1. Checking models.py...")
    try:
        with open('app/models.py', 'r', encoding='utf-8') as f:  # ✅ UTF-8 encoding
            content = f.read()
            
        has_sqlalchemy = 'from sqlalchemy' in content
        has_base = 'class MonitoringJob(Base)' in content or 'class MonitoringEvent(Base)' in content
        
        if has_sqlalchemy or has_base:
            print("   ❌ WRONG: models.py still has SQLAlchemy code")
            all_correct = False
        else:
            print("   ✅ CORRECT: models.py is Pydantic-only")
    except Exception as e:
        print(f"   ⚠️  ERROR: {e}")
        all_correct = False
    
    # 2. Check database.py
    print("\n2. Checking database.py...")
    try:
        with open('app/database.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_local_import = 'from app.db_models import MonitoringJob' in content
        
        if has_local_import:
            print("   ✅ CORRECT: database.py has local imports in init_db()")
        else:
            print("   ⚠️  WARNING: Couldn't verify database.py structure")
    except Exception as e:
        print(f"   ⚠️  ERROR: {e}")
        all_correct = False
    
    # 3. Check events.py
    print("\n3. Checking events.py...")
    try:
        with open('app/events.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_while_true = 'while True:' in content and 'yield' in content
        has_broken_return = 'return await _event_queue.get()' in content
        
        if has_broken_return:
            print("   ❌ WRONG: events.py has broken 'return await' pattern")
            all_correct = False
        elif has_while_true:
            print("   ✅ CORRECT: events.py has proper async generator")
        else:
            print("   ⚠️  WARNING: Couldn't verify events.py structure")
    except Exception as e:
        print(f"   ⚠️  ERROR: {e}")
        all_correct = False
    
    # 4. Check alert_store.py
    print("\n4. Checking alert_store.py...")
    try:
        with open('app/alert_store.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_async_save = 'async def save_alert(' in content
        
        if not has_async_save:
            print("   ❌ WRONG: alert_store.py save_alert() is not async")
            all_correct = False
        else:
            print("   ✅ CORRECT: alert_store.py has async save_alert()")
    except Exception as e:
        print(f"   ⚠️  ERROR: {e}")
        all_correct = False
    
    # 5. Check alert_processor.py
    print("\n5. Checking alert_processor.py...")
    try:
        with open('app/alert_processor.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        start_count = content.count('async def start(')
        
        if start_count > 1:
            print(f"   ❌ WRONG: alert_processor.py has {start_count} start() methods")
            all_correct = False
        elif start_count == 1:
            print("   ✅ CORRECT: alert_processor.py has single start() method")
        else:
            print("   ⚠️  WARNING: No start() method found")
            all_correct = False
    except Exception as e:
        print(f"   ⚠️  ERROR: {e}")
        all_correct = False
    
    # 6. Check monitoring_worker.py
    print("\n6. Checking monitoring_worker.py...")
    try:
        with open('app/monitoring_worker.py', 'r', encoding='utf-8') as f:
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
        print(f"   ⚠️  ERROR: {e}")
        all_correct = False
    
    # Final result
    print("\n" + "=" * 70)
    if all_correct:
        print("✅ ALL FILES VERIFIED - Ready to test!")
        print("=" * 70)
        print("\nNext step: Start the application")
        print("  uv run python -m app.main")
        return 0
    else:
        print("❌ SOME FILES NEED UPDATES")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(check_file_signatures())