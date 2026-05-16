from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# 🔌 DATABASE ENGINE INITIALIZATION
# Switches natively to a local SQLite instance container file
DATABASE_URL = "sqlite:///./pos.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Required for SQLite concurrent multi-threading requests
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 🔒 IDENTITY MATRIX MODEL: Stores credentials, system access roles, and shop brand graphics
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False)  # admin, cashier, livreur, client
    password_hash = Column(String, nullable=False)
    
    # 🖼️ BRAND ARCHIVE COLUMN: Holds the relative asset path location for shop/user profile graphics
    logo_url = Column(String, default="/static/products/placeholder.png")


# 📦 WAREHOUSE INVENTORY MODEL: Tracks barcodes, stock balances, velocities, and item imagery
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    
    # 🖼️ MASTER CATALOG MEDIA COLUMN: Holds file addresses generated inside the ingestion engine
    image_url = Column(String, default="/static/products/placeholder.png")


# 📥 B2B LOGISTICS SUPPLY MANIFEST MODEL: Maps remote incoming wholesale shop orders and coordinates
class ShopOrder(Base):
    __tablename__ = "shop_orders"

    id = Column(Integer, primary_key=True, index=True)
    shop_name = Column(String, nullable=False)
    items_summary = Column(String, nullable=False)  # Parsed array summary strings (e.g., "5x Organic Beans")
    total_price = Column(Float, nullable=False)
    status = Column(String, default="Pending")  # Pending, Completed (Dispatched), Delivered
    
    # 📍 COORDINATE GEOMETRY CHANNELS: Maps locations to calculate route vectors on Leaflet maps
    gps_latitude = Column(Float, nullable=False)
    gps_longitude = Column(Float, nullable=False)
    
    store_photo_url = Column(String, default="https://images.unsplash.com/photo-1578916171728-46686eac8d58?q=80&w=200")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


# 🧾 COUNTER RETAIL HISTORY MODEL: Commits walk-in cash sales directly to the Lvant Direct audit ledger
class HistoricalSale(Base):
    __tablename__ = "historical_sales"

    id = Column(Integer, primary_key=True, index=True)
    total_amount = Column(Float, nullable=False)  # Tracks gross bill values (including 8% retail VAT metrics)
    items_json = Column(String, nullable=False)    # Raw dumped cart strings containing structural rows
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


# 🚀 ARCHITECTURAL BOOTSTRAPPER: Compiles schemas and binds tables to engine resources
def init_db():
    # 🛠️ FIXED: Swapped 'create_base_all' to 'create_all'
    Base.metadata.create_all(bind=engine)
    print("✨ Core Database Matrix Schema initialized and locked to pos.db.")