# from models import Base, engine
# from models.admin import Admin
# from models.client import Client
# from models.category import Category
# from models.product import Product
# from models.bill import Bill
# from models.bill_item import BillItem
# from models.payment import Payment
# from models.stock_alert import StockAlert
# from models.notification import Notification
# from sqlalchemy import text

# def init_db():
#     """Initialiser la base de données (créer toutes les tables)"""
#     print("🔄 Création des tables de la base de données PostgreSQL...")
#     try:
#         Base.metadata.create_all(bind=engine)
#         print("✅ Tables créées avec succès!")
        
#         # Afficher les tables créées
#         with engine.connect() as conn:
#             result = conn.execute(text("""
#                 SELECT table_name 
#                 FROM information_schema.tables 
#                 WHERE table_schema = 'public'
#                 ORDER BY table_name;
#             """))
#             tables = [row[0] for row in result]
#             print(f"📊 Tables créées: {', '.join(tables)}")
            
#     except Exception as e:
#         print(f"❌ Erreur lors de la création des tables: {str(e)}")
#         raise

# def drop_db():
#     """Supprimer toutes les tables de la base de données"""
#     print("⚠️  Suppression de toutes les tables...")
#     try:
#         Base.metadata.drop_all(bind=engine)
#         print("✅ Tables supprimées avec succès!")
#     except Exception as e:
#         print(f"❌ Erreur lors de la suppression des tables: {str(e)}")
#         raise

# def reset_db():
#     """Réinitialiser la base de données (supprimer et recréer toutes les tables)"""
#     print("🔄 Réinitialisation de la base de données PostgreSQL...")
#     drop_db()
#     init_db()
#     print("✅ Base de données réinitialisée avec succès!")

# def check_connection():
#     """Vérifier la connexion à la base de données PostgreSQL"""
#     print("🔍 Vérification de la connexion à PostgreSQL...")
#     try:
#         with engine.connect() as conn:
#             result = conn.execute(text("SELECT version();"))
#             version = result.scalar()
#             print(f"✅ Connexion réussie!")
#             print(f"📌 Version PostgreSQL: {version}")
#             return True
#     except Exception as e:
#         print(f"❌ Erreur de connexion: {str(e)}")
#         print("\n💡 Vérifiez:")
#         print("   1. PostgreSQL est installé et en cours d'exécution")
#         print("   2. La base de données existe")
#         print("   3. Les credentials dans .env sont corrects")
#         print("   4. Le port 5432 est accessible")
#         return False

# def create_sample_data():
#     """Créer des données de test (optionnel)"""
#     from sqlalchemy.orm import Session
#     from utils.auth import hash_password
#     from decimal import Decimal
    
#     print("🎲 Création de données de test...")
    
#     session = Session(bind=engine)
    
#     try:
#         # Créer un admin de test
#         admin = Admin(
#             username="admin",
#             email="admin@ecommerce.dz",
#             password_hash=hash_password("admin123"),
#             phone_number="+213555123456"
#         )
#         session.add(admin)
#         session.flush()
        
#         # Créer un client de test
#         client = Client(
#             username="client_test",
#             email="client@example.dz",
#             password_hash=hash_password("client123"),
#             phone_number="+213555654321",
#             address="123 Rue de la République",
#             city="Ouargla"
#         )
#         session.add(client)
#         session.flush()
        
#         # Créer des catégories
#         categories = [
#             Category(name="Électronique", description="Produits électroniques"),
#             Category(name="Vêtements", description="Vêtements et accessoires"),
#             Category(name="Alimentation", description="Produits alimentaires"),
#         ]
#         session.add_all(categories)
#         session.flush()
        
#         # Créer des produits
#         products = [
#             Product(
#                 name="Ordinateur Portable",
#                 description="Laptop haute performance",
#                 price=Decimal("85000.00"),
#                 quantity_in_stock=10,
#                 minimum_stock_level=3,
#                 category_id=categories[0].id,
#                 admin_id=admin.id
#             ),
#             Product(
#                 name="Smartphone",
#                 description="Téléphone dernière génération",
#                 price=Decimal("45000.00"),
#                 quantity_in_stock=25,
#                 minimum_stock_level=5,
#                 category_id=categories[0].id,
#                 admin_id=admin.id
#             ),
#             Product(
#                 name="T-Shirt",
#                 description="T-shirt en coton",
#                 price=Decimal("1500.00"),
#                 quantity_in_stock=50,
#                 minimum_stock_level=10,
#                 category_id=categories[1].id,
#                 admin_id=admin.id
#             ),
#         ]
#         session.add_all(products)
        
#         session.commit()
        
#         print("✅ Données de test créées!")
#         print(f"   👤 Admin: admin@ecommerce.dz / admin123")
#         print(f"   👥 Client: client@example.dz / client123")
#         print(f"   📦 {len(products)} produits créés")
        
#     except Exception as e:
#         session.rollback()
#         print(f"❌ Erreur lors de la création des données de test: {str(e)}")
#     finally:
#         session.close()

# if __name__ == "__main__":
#     import sys
    
#     if len(sys.argv) > 1:
#         command = sys.argv[1]
        
#         if command == "init":
#             check_connection()
#             init_db()
#         elif command == "drop":
#             drop_db()
#         elif command == "reset":
#             check_connection()
#             reset_db()
#         elif command == "check":
#             check_connection()
#         elif command == "sample":
#             check_connection()
#             init_db()
#             create_sample_data()
#         else:
#             print("❌ Commande inconnue. Utilisez: init, drop, reset, check, ou sample")
#     else:
#         print("""
# Usage:
#   python utils/db.py init    - Créer les tables
#   python utils/db.py drop    - Supprimer les tables
#   python utils/db.py reset   - Réinitialiser la DB
#   python utils/db.py check   - Vérifier la connexion
#   python utils/db.py sample  - Créer des données de test
#         """)