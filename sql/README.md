# Database Setup Instructions

This directory contains SQL scripts for setting up the PostgreSQL database for the FastAPI/Streamlit chat application.

## Connection Details

- **Host**: localhost
- **Port**: 5432
- **Database**: postgres
- **Username**: streamlitdemo
- **Password**: streamlitdemo

## Running the Scripts

1. To set up the database schema and initial data, run:

```bash
psql -U streamlitdemo -d postgres -f setup.sql
```

2. Alternatively, run each script in sequence:

```bash
psql -U streamlitdemo -d postgres -f 01_schema.sql
psql -U streamlitdemo -d postgres -f 02_seed_data.sql
```

## Schema Overview

The database includes the following tables:

- **users**: For authentication and API key management
- **chats**: To store chat sessions
- **messages**: To store individual messages within chats
- **system_prompts**: To store system prompts
- **rate_limits**: To track API usage for rate limiting

## Notes

- The default admin user has username `admin` and password `admin` (should be changed in production)
- In a production environment, ensure proper security measures are implemented:
  - Use strong, hashed passwords
  - Secure the database connection
  - Properly handle API keys and credentials