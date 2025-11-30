# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from contextlib import asynccontextmanager

# # Import des routers
# from routers import (
#     admin_router,
#     client_router,
#     category_router,
#     product_router,
#     bill_router,
#     payment_router,
#     stock_alert_router,
#     notification_router,
#     auth_router,
#     otp_rout

# )

# # Import de l'initialisation de la base de données
# from utils.db import create_sample_data, init_db, test_connection
# from dotenv import load_dotenv
# import os
# load_dotenv()

# # Événement de démarrage pour initialiser la base de données


# # @asynccontextmanager
# # async def lifespan(app: FastAPI):
# #     # Au démarrage
# #     print("🚀 Démarrage de l'application...")
# #     print("📊 Initialisation de la base de données...")
# #     init_db()
# #     print("✅ Base de données initialisée avec succès!")
# #     yield
# #     # Au arrêt
# #     print("👋 Arrêt de l'application...")

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     print("=" * 60)
#     print("🚀 Starting E-Commerce API...")
#     print("=" * 60)

#     # Test database connection
#     if test_connection():
#         print("📊 Database migrations managed by Alembic")
#         print("💡 Run 'alembic upgrade head' to apply migrations")
#     else:
#         print("⚠️  Database connection failed, but continuing...")

#     print("=" * 60)
#     yield

#     # Shutdown
#     print("=" * 60)
#     print("👋 Shutting down E-Commerce API...")
#     print("=" * 60)

# # Créer l'application FastAPI
# app = FastAPI(
#     title="Système de Gestion E-Commerce",
#     description="""
#     ## API de gestion e-commerce avec FastAPI
    
#     ### Fonctionnalités principales:
#     * **Gestion des administrateurs** - Inscription, connexion, gestion des admins
#     * **Gestion des clients** - Inscription, connexion, profils clients
#     * **Gestion des catégories** - CRUD complet des catégories de produits
#     * **Gestion des produits** - CRUD, gestion de stock, alertes automatiques
#     * **Gestion des factures** - Création, consultation, suivi des paiements
#     * **Gestion des paiements** - Paiements multiples, historique, mise à jour
#     * **Alertes de stock** - Notifications automatiques pour stock faible
#     * **Système de notifications** - Email et WhatsApp pour admins et clients
    
#     ### Authentification:
#     L'API utilise JWT (JSON Web Tokens) pour l'authentification.
    
#     ### Note:
#     Tous les messages de l'API sont en français.
#     """,
#     version="1.0.0",
#     lifespan=lifespan,
#     docs_url="/docs",
#     redoc_url="/redoc"
# )

# # Configuration CORS (Cross-Origin Resource Sharing)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # En production, spécifiez les domaines autorisés
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Route de base


# @app.get("/", tags=["Root"])
# async def root():
#     """Route de base pour vérifier que l'API fonctionne"""
#     return {
#         "message": "Bienvenue sur l'API E-Commerce",
#         "version": "1.0.0",
#         "status": "En ligne",
#         "documentation": "/docs",
#         "endpoints": {
#             "admin": "/admin",
#             "client": "/client",
#             "category": "/category",
#             "product": "/product",
#             "bill": "/bill",
#             "payment": "/payment",
#             "stock_alert": "/stock-alert",
#             "notification": "/notification"
#         }
#     }

# # Route de santé


# @app.get("/health", tags=["Health"])
# async def health_check():
#     """Vérifier l'état de santé de l'API"""
#     return {
#         "status": "healthy",
#         "message": "L'API fonctionne correctement"
#     }


# @app.post("/initial_data", tags=["initial_data"])
# def initila_data():
#     create_sample_data()
#     return {
#         "status": "seccess initialed",
#         "message": "initialed successfully"
#     }

# # Gestionnaire d'erreurs global


# @app.exception_handler(HTTPException)
# async def http_exception_handler(request, exc):
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={
#             "error": True,
#             "message": exc.detail,
#             "status_code": exc.status_code
#         }
#     )


# @app.exception_handler(Exception)
# async def general_exception_handler(request, exc):
#     return JSONResponse(
#         status_code=500,
#         content={
#             "error": True,
#             "message": "Une erreur interne s'est produite",
#             "details": str(exc)
#         }
#     )

# # Enregistrer tous les routers
# app.include_router(admin_router)
# app.include_router(client_router)
# app.include_router(category_router)
# app.include_router(product_router)
# app.include_router(bill_router)
# app.include_router(payment_router)
# app.include_router(stock_alert_router)
# app.include_router(notification_router)
# app.include_router(auth_router)
# app.include_router(otp_rout)


# # Point d'entrée pour exécuter l'application
# if __name__ == "__main__":
#     import uvicorn

#     print("""
#     ╔═══════════════════════════════════════════════════════════╗
#     ║                                                           ║
#     ║         🚀 API E-Commerce - Système de Gestion           ║
#     ║                                                           ║
#     ║  📍 Serveur local: http://localhost:8000                 ║
#     ║  📚 Documentation: http://localhost:8000/docs            ║
#     ║  📖 ReDoc: http://localhost:8000/redoc                   ║
#     ║                                                           ║
#     ╚═══════════════════════════════════════════════════════════╝
#     """)

#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,  # Auto-reload en développement
#         log_level="info"
#     )
