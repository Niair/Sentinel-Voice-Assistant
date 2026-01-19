const postgres = require('postgres');
require('dotenv').config({ path: '.env.local' });

async function test() {
      console.log('Testing connection to:', process.env.POSTGRES_URL);
      const sql = postgres(process.env.POSTGRES_URL);

      try {
            const result = await sql`SELECT 1+1 AS result`;
            console.log('Connection successful:', result);

            const user = await sql`SELECT * FROM "User" LIMIT 1`;
            console.log('User found:', user);
      } catch (err) {
            console.error('Connection failed:', err);
      } finally {
            await sql.end();
      }
}

test();
