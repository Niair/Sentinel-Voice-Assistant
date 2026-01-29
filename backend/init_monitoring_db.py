"""
Database migration script - Create monitoring tables.

Usage:
    python init_monitoring_db.py

This script will:
1. Create monitoring_jobs, monitoring_events, monitoring_alerts tables
2. Create necessary indexes
3. Verify table creation
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import init_db, engine
from app.models import MonitoringJob, MonitoringEvent, MonitoringAlert


async def main():
    """Run database initialization"""
    print("🔄 Starting database migration...")
    print(f"📊 Database: {engine.url}")
    
    try:
        # Create all tables
        await init_db()
        
        # Verify tables exist
        async with engine.connect() as conn:
            from sqlalchemy import text
            
            result = await conn.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE 'monitoring_%'
                    ORDER BY table_name
                """)
            )
            
            tables = [row[0] for row in result]
            
            if len(tables) == 3:
                print("\n✅ Migration successful! Created tables:")
                for table in tables:
                    print(f"   - {table}")
            else:
                print(f"\n⚠️ Warning: Expected 3 tables, found {len(tables)}")
                for table in tables:
                    print(f"   - {table}")
        
        print("\n✅ Database is ready for monitoring system!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())