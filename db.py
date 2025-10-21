from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database2.db")

# Render uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"✅ Using database: {'PostgreSQL (Production)' if 'postgresql' in DATABASE_URL else 'SQLite (Development)'}")