-- Main setup script to initialize the database

-- Connect to the database
\c postgres;

-- Load schema
\i '/app/sql/01_schema.sql'

-- Load seed data
\i '/app/sql/02_seed_data.sql'

-- Grant privileges to the streamlitdemo user
GRANT ALL PRIVILEGES ON DATABASE postgres TO streamlitdemo;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO streamlitdemo;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO streamlitdemo;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO streamlitdemo;