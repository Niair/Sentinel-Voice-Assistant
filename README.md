# GAIP

      git status
      
      git add .
      
      git commit -m "Day-
      
      git push -u origin main

# once
pip install uv

# per project
uv venv -p 3.11
.venv\Scripts\activate
uv pip install -r requirements.txt

# start
backend: uv run python -m app.main
frontend: pnpm dev 

-----------------------------------------------------------------------------------

docker rm -f sentinel-postgres

docker run -d --name sentinel-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres -p 5442:5432 postgres:15-alpine

docker ps

-----------------------------------------------------------------------------------

frontend:
npx drizzle-kit push --config=drizzle.config.ts

-----------------------------------------------------------------------------------

# 1. Reset locally
git reset --hard 5df35df

# 2. Force push to update the remote (WARNING: This rewrites history)
git push -f origin main

-----------------------------------------------------------------------------------

# If Postgres is running in Docker
docker exec -i sentinel-postgres psql -U postgres -d postgres < create_monitoring_tables.sql

# Or directly with psql
psql -U postgres -d postgres -f create_monitoring_tables.sql

docker exec -it sentinel-postgres psql -U postgres -d postgres
\dt monitoring_*

-- Should show:
-- monitoring_jobs
-- monitoring_events  
-- monitoring_alerts

-----------------------------------------------------------------------------------

backend logs:

backend> set PYTHONPATH=. && python tests\test_event_bus.py

-----------------------------------------------------------------------------------

test:

backend> set PYTHONPATH=. && python tests/test_database_connection.py

ok 