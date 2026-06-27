# models/store_user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from utils.db import Base


class StoreUserRole(str, enum.Enum):
    admin = "admin"
    livreur = "livreur"


class StoreUser(Base):
    """
    User account for the website/ecommerce dashboard.
    Completely separate from the B2B Admin and Client tables.

    Roles:
      - admin   : full access to all orders, can manage livreurs,
                  can hide orders from livreurs, can delete orders.
      - livreur : sees only visible (non-hidden) orders,
                  can update delivery/calling status and add notes.
                  Cannot delete orders.
    """

    __tablename__ = "store_users"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)

    role = Column(
        SAEnum(StoreUserRole, name="store_user_role"),
        nullable=False,
        default=StoreUserRole.livreur,
    )

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Back-reference: orders assigned/visible to this livreur
    # (via EcommerceOrder.assigned_livreur_id)
    assigned_orders = relationship(
        "EcommerceOrder",
        foreign_keys="EcommerceOrder.assigned_livreur_id",
        back_populates="assigned_livreur",
        lazy="dynamic",
    )
