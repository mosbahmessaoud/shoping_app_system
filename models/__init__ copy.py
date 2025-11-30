# """
# Database configuration and session management
# Dynamic configuration for local development and Railway deployment
# """
# import os
# from sqlalchemy import create_engine, text
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # Get DATABASE_URL from environment
# DATABASE_URL = os.getenv("DATABASE_URL")

# # Railway PostgreSQL URL fix (Railway uses postgres:// but SQLAlchemy needs postgresql://)
# if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
#     DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
#     print("🚂 Detected Railway PostgreSQL URL, converted to postgresql://")

# # Fallback to local database if no DATABASE_URL provided
# if not DATABASE_URL:
#     DATABASE_URL = os.getenv(
#         "LOCAL_DATABASE_URL",
#         "postgresql://postgres:032023@localhost:5432/Ecom_app"
#     )
#     print(
#         f"💻 Using local database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
# else:
#     # Mask password in production URL for security
#     masked_url = DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else '***'
#     print(f"☁️ Using production database: {masked_url}")

# # Engine configuration
# engine_kwargs = {
#     "pool_pre_ping": True,  # Verify connections before using
#     "pool_recycle": 3600,   # Recycle connections after 1 hour
#     # Log SQL queries if SQL_ECHO=true
#     "echo": os.getenv("SQL_ECHO", "False").lower() == "true",
# }

# # SQLite configuration (if you ever need it for testing)
# if DATABASE_URL.startswith("sqlite"):
#     engine_kwargs["connect_args"] = {"check_same_thread": False}
# else:
#     # PostgreSQL specific configuration
#     engine_kwargs.update({
#         "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
#         "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
#         "pool_timeout": 30,
#     })

# # Create engine
# engine = create_engine(DATABASE_URL, **engine_kwargs)

# # Session factory
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # Base class for models
# Base = declarative_base()


# def get_db():
#     """
#     Database session dependency for FastAPI
#     Usage in routes: db: Session = Depends(get_db)
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# def test_connection():
#     """
#     Test database connection
#     Returns True if connection is successful, False otherwise
#     """
#     try:
#         with engine.connect() as conn:
#             result = conn.execute(text("SELECT version();"))
#             version = result.scalar()
#             print(f"✅ Database connected successfully!")
#             print(f"📌 PostgreSQL version: {version[:50]}...")
#             return True
#     except Exception as e:
#         print(f"❌ Database connection failed: {str(e)}")
#         print("\n💡 Troubleshooting:")
#         print("   - Check if PostgreSQL is running (local)")
#         print("   - Verify DATABASE_URL in .env")
#         print("   - Check Railway database credentials")
#         return False
