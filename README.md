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


npx drizzle-kit push --config=drizzle.config.ts