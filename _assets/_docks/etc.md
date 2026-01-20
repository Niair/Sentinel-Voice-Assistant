1. How to start Postgres on port 5442
Open your terminal in the root directory (
E:_Projects\Sentinal-Voice-Assistant
) and run:

bash
docker compose up -d
What this does:

-d: Runs in the background (detached mode).
Maps your local port 5442 to the database's internal port 5432.
Sets the username/password to postgres/postgres (matching your 
.env.local
).
2. How to initialize/push your schema
Once the database is running, you need to create the tables. Since you are using Drizzle ORM, run this in the frontend folder:

bash
cd frontend
pnpm db:push
3. Verify Connection
You can now run your test script again to confirm everything is working:

bash
node test-db.js