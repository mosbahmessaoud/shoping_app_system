from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("LOCAL_DATABASE_URL") or os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

tables = [
    'notifications', 'stock_alerts', 'payments', 'bill_items', 
    'bills', 'products', 'categories', 'clients', 'admins', 'alembic_version'
]

with engine.connect() as conn:
    for table in tables:
        try:
            conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            print(f"✅ Dropped {table}")
        except Exception as e:
            print(f"⚠️ Error dropping {table}: {e}")
    conn.commit()
    print("\n🎉 All tables dropped! Now run: alembic revision --autogenerate -m 'Initial migration'")