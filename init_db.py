import psycopg2
import os

def get_db():
    conn = psycopg2.connect(os.environ.get("SUPABASE_URL"))
    return conn
