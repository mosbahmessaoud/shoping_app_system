from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("LOCAL_DATABASE_URL") or os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("DELETE FROM alembic_version"))
    conn.commit()
    print("✅ Alembic version table cleared!")