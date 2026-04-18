#!/usr/bin/env python3
"""
PostgreSQL + pgvector setup script for Windows.
Sets up the news_db database with pgvector extension.
"""

import sys
import os
from pathlib import Path

def setup_pgvector():
    """Set up PostgreSQL database and pgvector extension."""
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed. Installing...", file=sys.stderr)
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg[binary]"])
        import psycopg

    print("=" * 60)
    print("PostgreSQL + pgvector Setup")
    print("=" * 60)

    # Connection parameters
    host = input("\nPostgreSQL Host (default: localhost): ").strip() or "localhost"
    port = input("PostgreSQL Port (default: 5432): ").strip() or "5432"
    default_db = input("Default database (default: postgres): ").strip() or "postgres"
    user = input("PostgreSQL User (default: postgres): ").strip() or "postgres"
    password = input("PostgreSQL Password: ").strip()

    print("\nConnecting to PostgreSQL...")
    try:
        # Connect to default postgres database
        conn = psycopg.connect(
            host=host,
            port=port,
            database=default_db,
            user=user,
            password=password,
            autocommit=True
        )
        cursor = conn.cursor()
        print("✓ Connected successfully")
    except psycopg.OperationalError as e:
        print(f"✗ Connection failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Create database
    print("\nSetting up news_db database...")
    try:
        cursor.execute("DROP DATABASE IF EXISTS news_db;")
        print("✓ Dropped existing news_db (if any)")
    except Exception as e:
        print(f"  Note: {e}")

    try:
        cursor.execute("CREATE DATABASE news_db;")
        print("✓ Created news_db database")
    except Exception as e:
        print(f"✗ Failed to create database: {e}", file=sys.stderr)
        cursor.close()
        conn.close()
        sys.exit(1)

    cursor.close()
    conn.close()

    # Connect to news_db and set up pgvector
    print("\nConnecting to news_db...")
    try:
        conn = psycopg.connect(
            host=host,
            port=port,
            database="news_db",
            user=user,
            password=password,
            autocommit=True
        )
        cursor = conn.cursor()
        print("✓ Connected to news_db")
    except psycopg.OperationalError as e:
        print(f"✗ Failed to connect to news_db: {e}", file=sys.stderr)
        sys.exit(1)

    # Create pgvector extension
    print("\nSetting up pgvector extension...")
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("✓ pgvector extension created/enabled")
    except Exception as e:
        print(f"✗ Failed to create pgvector extension: {e}", file=sys.stderr)
        print("  Note: pgvector may need to be installed separately via PostgreSQL extensions.", file=sys.stderr)
        cursor.close()
        conn.close()
        sys.exit(1)

    # Create article_embeddings table
    print("\nCreating article_embeddings table...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS article_embeddings (
                item_id TEXT PRIMARY KEY,
                embedding VECTOR(768) NOT NULL
            );
        """)
        print("✓ article_embeddings table created")
    except Exception as e:
        print(f"✗ Failed to create table: {e}", file=sys.stderr)
        cursor.close()
        conn.close()
        sys.exit(1)

    # Verify setup
    print("\nVerifying setup...")
    try:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✓ PostgreSQL: {version.split(',')[0]}")

        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        if cursor.fetchone():
            print("✓ pgvector extension is active")
        else:
            print("✗ pgvector extension not found", file=sys.stderr)

        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'article_embeddings';")
        if cursor.fetchone()[0] > 0:
            print("✓ article_embeddings table exists")
        else:
            print("✗ article_embeddings table not found", file=sys.stderr)
    except Exception as e:
        print(f"✗ Verification failed: {e}", file=sys.stderr)

    cursor.close()
    conn.close()

    # Generate .env configuration
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)

    db_url = f"postgresql://{user}:{password}@{host}:{port}/news_db"
    env_content = f"""# PostgreSQL Vector Store Configuration
VECTOR_STORE_BACKEND=pgvector
VECTOR_STORE_DATABASE_URL={db_url}
VECTOR_STORE_DIMENSION=768
VECTOR_STORE_TABLE_NAME=article_embeddings

# Live Ingestion
LIVE_INGESTION_ENABLED=true
NEWS_API_KEY=<set_in_local_env>
"""

    env_path = Path(__file__).parent / ".env"
    with open(env_path, "a") as f:
        f.write("\n" + env_content)

    print(f"\n✓ Configuration added to .env:")
    print(env_content)
    print(f"\nYou can now run:")
    print("  cd backend")
    print("  python -m pytest tests/test_pgvector_optional_integration.py -v")

if __name__ == "__main__":
    setup_pgvector()
