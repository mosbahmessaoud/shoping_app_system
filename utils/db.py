"""
Database configuration, session management, and utility functions
Dynamic configuration for local development and Railway deployment
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Railway PostgreSQL URL fix (Railway uses postgres:// but SQLAlchemy needs postgresql://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print("🚂 Detected Railway PostgreSQL URL, converted to postgresql://")

# Fallback to local database if no DATABASE_URL provided
if not DATABASE_URL:
    DATABASE_URL = os.getenv(
        "LOCAL_DATABASE_URL",
        "postgresql://postgres:032023@localhost:5432/Ecom_app"
    )
    print(
        f"💻 Using local database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
else:
    # Mask password in production URL for security
    masked_url = DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else '***'
    print(f"☁️ Using production database: {masked_url}")

# Engine configuration
engine_kwargs = {
    "pool_pre_ping": True,  # Verify connections before using
    "pool_recycle": 3600,   # Recycle connections after 1 hour
    # Log SQL queries if SQL_ECHO=true
    "echo": os.getenv("SQL_ECHO", "False").lower() == "true",
}

# SQLite configuration (if you ever need it for testing)
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL specific configuration
    engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_timeout": 30,
    })

# Create engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Database session dependency for FastAPI
    Usage in routes: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """
    Test database connection
    Returns True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ Database connected successfully!")
            print(f"📌 PostgreSQL version: {version[:50]}...")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        print("\n💡 Troubleshooting:")
        print("   - Check if PostgreSQL is running (local)")
        print("   - Verify DATABASE_URL in .env")
        print("   - Check Railway database credentials")
        return False


def init_db():
    """Initialiser la base de données (créer toutes les tables)"""
    from models.admin import Admin
    from models.client import Client
    from models.category import Category
    from models.product import Product
    from models.bill import Bill
    from models.bill_item import BillItem
    from models.payment import Payment
    from models.stock_alert import StockAlert
    from models.notification import Notification
    
    print("🔄 Création des tables de la base de données PostgreSQL...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables créées avec succès!")
        
        # Afficher les tables créées
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            print(f"📊 Tables créées: {', '.join(tables)}")
            
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {str(e)}")
        raise


def drop_db():
    """Supprimer toutes les tables de la base de données"""
    print("⚠️  Suppression de toutes les tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        print("✅ Tables supprimées avec succès!")
    except Exception as e:
        print(f"❌ Erreur lors de la suppression des tables: {str(e)}")
        raise


def reset_db():
    """Réinitialiser la base de données (supprimer et recréer toutes les tables)"""
    print("🔄 Réinitialisation de la base de données PostgreSQL...")
    drop_db()
    init_db()
    print("✅ Base de données réinitialisée avec succès!")


def check_connection():
    """Vérifier la connexion à la base de données PostgreSQL"""
    print("🔍 Vérification de la connexion à PostgreSQL...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ Connexion réussie!")
            print(f"📌 Version PostgreSQL: {version}")
            return True
    except Exception as e:
        print(f"❌ Erreur de connexion: {str(e)}")
        print("\n💡 Vérifiez:")
        print("   1. PostgreSQL est installé et en cours d'exécution")
        print("   2. La base de données existe")
        print("   3. Les credentials dans .env sont corrects")
        print("   4. Le port 5432 est accessible")
        return False


def create_sample_data():
    """Créer des données de test (optionnel)"""
    from utils.auth import hash_password
    from decimal import Decimal
    from models.admin import Admin
    from models.client import Client
    from models.category import Category
    from models.product import Product
    
    print("🎲 Création de données de test...")
    
    session = Session(bind=engine)
    
    try:
        # Créer un admin de test
        admin = Admin(
            username="admin",
            email="admin@ecommerce.dz",
            password_hash=hash_password("admin123"),
            phone_number="+213555123456"
        )
        session.add(admin)
        session.flush()
        
        # Créer un client de test
        client = Client(
            username="client_test",
            email="client@example.dz",
            password_hash=hash_password("client123"),
            phone_number="+213555654321",
            address="123 Rue de la République",
            city="Ouargla"
        )
        session.add(client)
        session.flush()
        
        # Créer des catégories
        categories = [
            Category(name="Électronique", description="Produits électroniques"),
            Category(name="Vêtements", description="Vêtements et accessoires"),
            Category(name="Alimentation", description="Produits alimentaires"),
        ]
        session.add_all(categories)
        session.flush()
        
        # Créer des produits
        products = [
            Product(
                name="Ordinateur Portable",
                description="Laptop haute performance",
                price=Decimal("85000.00"),
                quantity_in_stock=10,
                minimum_stock_level=3,
                category_id=categories[0].id,
                admin_id=admin.id
            ),
            Product(
                name="Smartphone",
                description="Téléphone dernière génération",
                price=Decimal("45000.00"),
                quantity_in_stock=25,
                minimum_stock_level=5,
                category_id=categories[0].id,
                admin_id=admin.id
            ),
            Product(
                name="T-Shirt",
                description="T-shirt en coton",
                price=Decimal("1500.00"),
                quantity_in_stock=50,
                minimum_stock_level=10,
                category_id=categories[1].id,
                admin_id=admin.id
            ),
        ]
        session.add_all(products)
        
        session.commit()
        
        print("✅ Données de test créées!")
        print(f"   👤 Admin: admin@ecommerce.dz / admin123")
        print(f"   👥 Client: client@example.dz / client123")
        print(f"   📦 {len(products)} produits créés")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erreur lors de la création des données de test: {str(e)}")
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            check_connection()
            init_db()
        elif command == "drop":
            drop_db()
        elif command == "reset":
            check_connection()
            reset_db()
        elif command == "check":
            check_connection()
        elif command == "sample":
            check_connection()
            init_db()
            create_sample_data()
        else:
            print("❌ Commande inconnue. Utilisez: init, drop, reset, check, ou sample")
    else:
        print("""
Usage:
  python utils/db.py init    - Créer les tables
  python utils/db.py drop    - Supprimer les tables
  python utils/db.py reset   - Réinitialiser la DB
  python utils/db.py check   - Vérifier la connexion
  python utils/db.py sample  - Créer des données de test
        """)