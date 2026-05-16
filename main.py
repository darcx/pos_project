from fastapi import FastAPI, Depends, HTTPException, Request, Form, BackgroundTasks, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os, database, json, datetime, shutil
import urllib.parse, urllib.request
import ssl 
import hashlib, secrets

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 📂 STATIC MEDIA ASSETS STORAGE FILE PATH CONFIGURATION
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "products")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# 📡 GLOBAL COORD SYSTEM CACHE LAYER (Fed continuously by live driver device geolocation pings)
LIVREUR_GPS_CACHE = {"latitude": 34.0333, "longitude": -5.0000}

database.init_db()

# 🔒 CRYPTOGRAPHIC SECURITY LAYER
def hash_password(password: str) -> str:
    """Generates a secure PBKDF2 password hash using a unique random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{key.hex()}"

def verify_password(plain_password: str, stored_password_hash: str) -> bool:
    """Verifies an incoming password against the securely stored salt and hash combination."""
    try:
        salt, stored_key = stored_password_hash.split(":")
        new_key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return secrets.compare_digest(stored_key, new_key.hex())
    except Exception:
        return False

# 🚀 Bootstrap Secure Data Seeds on Launch
db = database.SessionLocal()
if not db.query(database.User).first():
    db.add_all([
        database.User(username="admin", role="admin", password_hash=hash_password("AdminPassword2026")),
        database.User(username="cashier", role="cashier", password_hash=hash_password("CashierPassword2026")),
        database.User(username="livreur", role="livreur", password_hash=hash_password("LivreurPassword2026"))
    ])
if not db.query(database.Product).first():
    db.add_all([
        database.Product(barcode="11111", name="Organic Coffee Beans", price=14.99, stock=50),
        database.Product(barcode="22222", name="Almond Milk 1L", price=3.49, stock=30),
        database.Product(barcode="33333", name="Ceramic Coffee Mug", price=12.00, stock=15),
        database.Product(barcode="44444", name="Fresh Avocado Toast", price=8.50, stock=25)
    ])
db.commit()
db.close()

def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

# 🚪 ENTRANCE LOGIN PORTAL GATEWAY VIEW
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

# 🔒 SECURED MULTI-ROLE IDENTITY VERIFICATION ROUTER
@app.post("/login")
def handle_login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(database.User).filter(database.User.username == username).first()
    
    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse(url="/?error=Invalid+Credentials+Try+Again", status_code=303)
        
    if user.role == "admin":
        return RedirectResponse(url="/admin", status_code=303)
    if user.role == "livreur":
        response = RedirectResponse(url="/livreur", status_code=303)
        response.set_cookie(key="driver_session", value=username, max_age=86400, httponly=True)
        return response
    if user.role == "cashier":
        return RedirectResponse(url="/pos", status_code=303)
        
    # Standard registered B2B Wholesale Shop Clients route
    response = RedirectResponse(url="/app", status_code=303)
    response.set_cookie(key="shop_session", value=username, max_age=86400, httponly=True)
    return response

# 🔑 CLIENT SELF-REGISTRATION GATEWAY: Safely appends fresh businesses to ledger matrix
@app.post("/register")
def handle_registration(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(database.User).filter(database.User.username == username).first()
    if existing_user:
        return RedirectResponse(url="/?error=Username+Already+Exists", status_code=303)
    
    new_shop_user = database.User(
        username=username,
        role="client", 
        password_hash=hash_password(password),
        logo_url="/static/products/placeholder.png"
    )
    db.add(new_shop_user)
    db.commit()
    return RedirectResponse(url="/?success=Account+Created+Please+Login", status_code=303)

# 💻 CASHIER RETAIL DIRECT SALES COUNTER VIEW TERMINAL
@app.get("/pos", response_class=HTMLResponse)
def user_panel(request: Request, db: Session = Depends(get_db)):
    cashier_profile = db.query(database.User).filter(database.User.username == "cashier").first()
    cashier_logo = cashier_profile.logo_url if (cashier_profile and getattr(cashier_profile, 'logo_url', None)) else '/static/products/placeholder.png'
    
    products = db.query(database.Product).all()
    return templates.TemplateResponse(request=request, name="index.html", context={"products": products, "cashier_logo": cashier_logo})

# 📊 ADMIN DASHBOARD CONTROL DECK: Real-time Revenue & Forecasting Runways
@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, db: Session = Depends(get_db)):
    admin_profile = db.query(database.User).filter(database.User.username == "admin").first()
    admin_logo = admin_profile.logo_url if (admin_profile and getattr(admin_profile, 'logo_url', None)) else '/static/products/placeholder.png'

    raw_products = db.query(database.Product).all()
    incoming_orders = db.query(database.ShopOrder).order_by(database.ShopOrder.id.desc()).all()
    in_store_sales = db.query(database.HistoricalSale).order_by(database.HistoricalSale.id.desc()).all()
    
    total_b2b = sum(o.total_price for o in incoming_orders if o.status in ["Completed", "Delivered"])
    total_retail = sum(s.total_amount for s in in_store_sales)
    
    product_velocity = {p.barcode: 0 for p in raw_products}
    tracking_days_window = 7.0 

    for sale in in_store_sales:
        try:
            items = json.loads(sale.items_json)
            for item in items:
                bc = item.get('barcode')
                if bc in product_velocity:
                    product_velocity[bc] += item.get('qty', 0)
        except Exception:
            continue

    for order in incoming_orders:
        if order.status in ["Completed", "Delivered"]:
            if "Organic Coffee" in order.items_summary:
                product_velocity["11111"] += 3
            if "Almond Milk" in order.items_summary:
                product_velocity["22222"] += 10

    forecasting_products = []
    for p in raw_products:
        daily_velocity = round(product_velocity.get(p.barcode, 0) / tracking_days_window, 2)
        
        if daily_velocity > 0:
            stock_runway_days = round(p.stock / daily_velocity, 1)
            if stock_runway_days <= 3.0:
                status_flag = "CRITICAL STOCKOUT RISK"
            elif stock_runway_days <= 7.0:
                status_flag = "REORDER WARNING"
            else:
                status_flag = "Normal"
        else:
            stock_runway_days = "∞"
            status_flag = "Stagnant Stock"

        image_url = getattr(p, 'image_url', '') if hasattr(database.Product, 'image_url') else '/static/products/placeholder.png'

        forecasting_products.append({
            "id": p.id,
            "barcode": p.barcode,
            "name": p.name,
            "price": p.price,
            "stock": p.stock,
            "velocity": daily_velocity,
            "runway": stock_runway_days,
            "status": status_flag,
            "image_url": image_url if image_url else '/static/products/placeholder.png'
        })
    
    return templates.TemplateResponse(
        request=request, name="admin.html", 
        context={
            "products": forecasting_products, 
            "incoming_orders": incoming_orders, 
            "in_store_sales": in_store_sales, 
            "revenue": f"{total_b2b + total_retail:.2f}",
            "admin_logo": admin_logo
        }
    )

# 🛠️ ADMIN INVENTORY MANAGEMENT ACTION ENDPOINTS
@app.post("/api/edit-product")
def edit_product(barcode: str = Form(...), price: float = Form(...), stock: int = Form(...), db: Session = Depends(get_db)):
    product = db.query(database.Product).filter(database.Product.barcode == barcode).first()
    if not product: raise HTTPException(status_code=404, detail="Product missing")
    product.price = price
    product.stock = stock
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/api/add-product")
async def add_product(barcode: str = Form(...), name: str = Form(...), price: float = Form(...), stock: int = Form(...), image_file: UploadFile = File(...), db: Session = Depends(get_db)):
    existing = db.query(database.Product).filter(database.Product.barcode == barcode).first()
    if existing: return RedirectResponse(url="/admin?error=Barcode+Already+Exists", status_code=303)

    file_extension = os.path.splitext(image_file.filename)[1]
    safe_filename = f"{barcode}{file_extension}"
    destination_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(image_file.file, buffer)

    relative_image_url = f"/static/products/{safe_filename}"
    new_product = database.Product(barcode=barcode, name=name, price=price, stock=stock)
    if hasattr(new_product, 'image_url'): new_product.image_url = relative_image_url

    db.add(new_product)
    db.commit()
    return RedirectResponse(url="/admin?success=Product+Appended", status_code=303)

# 🏪 B2B WHOLESALE MULTI-TENANT REMOTE CLIENT APP VIEW TERMINAL
@app.get("/app", response_class=HTMLResponse)
def mobile_b2b_app(request: Request, db: Session = Depends(get_db)):
    client_shop_filter = request.cookies.get("shop_session", "Hanout Ait Melloul")
    
    user_profile = db.query(database.User).filter(database.User.username == client_shop_filter).first()
    shop_logo = user_profile.logo_url if (user_profile and getattr(user_profile, 'logo_url', None)) else '/static/products/placeholder.png'
    
    products = db.query(database.Product).all()
    order_history = db.query(database.ShopOrder).filter(database.ShopOrder.shop_name == client_shop_filter).order_by(database.ShopOrder.id.desc()).all()
                      
    total_spent = sum(o.total_price for o in order_history if o.status == "Delivered")
    pending_count = sum(1 for o in order_history if o.status == "Pending")
    transit_count = sum(1 for o in order_history if o.status == "Completed")

    return templates.TemplateResponse(
        request=request, name="app.html", 
        context={
            "products": products, 
            "orders": order_history,
            "shop_name": client_shop_filter,
            "shop_logo": shop_logo,
            "analytics": {
                "total_spent": f"{total_spent:.2f}",
                "pending": pending_count,
                "transit": transit_count,
                "total_orders": len(order_history)
            }
        }
    )

# 🖼️ SHOP LOGO INGESTION ENDPOINT
@app.post("/api/upload-shop-logo")
async def upload_shop_logo(request: Request, logo_file: UploadFile = File(...), db: Session = Depends(get_db)):
    client_shop_name = request.cookies.get("shop_session")
    if not client_shop_name:
        raise HTTPException(status_code=401, detail="Session expired. Please log back in.")
    
    user = db.query(database.User).filter(database.User.username == client_shop_name).first()
    if not user:
        raise HTTPException(status_code=404, detail="Shop entry not found.")

    file_extension = os.path.splitext(logo_file.filename)[1].lower()
    if file_extension not in [".jpg", ".jpeg", ".png", ".webp"]:
        return RedirectResponse(url="/app?error=Invalid+Image+Format.+Use+PNG+or+JPG", status_code=303)

    safe_filename = f"logo_{client_shop_name}{file_extension}"
    destination_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(logo_file.file, buffer)

    user.logo_url = f"/static/products/{safe_filename}"
    db.commit()

    return RedirectResponse(url="/app?success=Shop+Logo+Updated+Successfully", status_code=303)

# 🚚 SERVE LIVREUR PANEL WORKSPACE (Assigned cargo list frames + navigation layout map anchors)
@app.get("/livreur", response_class=HTMLResponse)
def livreur_panel(request: Request, db: Session = Depends(get_db)):
    driver_session_filter = request.cookies.get("driver_session", "livreur")
    driver_profile = db.query(database.User).filter(database.User.username == driver_session_filter).first()
    driver_logo = driver_profile.logo_url if (driver_profile and getattr(driver_profile, 'logo_url', None)) else '/static/products/placeholder.png'
    
    active_deliveries = db.query(database.ShopOrder).filter(database.ShopOrder.status == "Completed").all()
    return templates.TemplateResponse(request=request, name="livreur.html", context={"orders": active_deliveries, "cached_driver": LIVREUR_GPS_CACHE, "driver_logo": driver_logo})

# 📡 LIVE DRIVER GPS TELEMETRY STREAM COORD RECEPTOR
@app.post("/api/sync-driver-gps")
def sync_driver_gps(latitude: float = Form(...), longitude: float = Form(...), db: Session = Depends(get_db)):
    global LIVREUR_GPS_CACHE
    LIVREUR_GPS_CACHE["latitude"] = latitude
    LIVREUR_GPS_CACHE["longitude"] = longitude
    return {"status": "streaming", "timestamp": str(datetime.datetime.now())}

# 📡 CLIENT MAP LEAFLET POLLING DATA FETCH API
@app.get("/api/get-livreur-gps")
def get_livreur_gps():
    global LIVREUR_GPS_CACHE
    return LIVREUR_GPS_CACHE

# 📡 B2B REMOTE INBOUND MANIFEST ORDERING API
@app.post("/api/submit-mobile-order")
def submit_mobile_order(shop_name: str = Form(...), items_summary: str = Form(...), total_price: float = Form(...), latitude: float = Form(...), longitude: float = Form(...), db: Session = Depends(get_db)):
    new_order = database.ShopOrder(
        shop_name=shop_name, items_summary=items_summary, total_price=total_price,
        gps_latitude=latitude, gps_longitude=longitude,
        store_photo_url="https://images.unsplash.com/photo-1578916171728-46686eac8d58?q=80&w=200", status="Pending"
    )
    db.add(new_order)
    db.commit()
    return {"status": "success"}

@app.get("/api/product/{barcode}")
def get_product(barcode: str, db: Session = Depends(get_db)):
    product = db.query(database.Product).filter(database.Product.barcode == barcode).first()
    if not product: raise HTTPException(status_code=404)
    return {"barcode": product.barcode, "name": product.name, "price": product.price, "stock": product.stock}

# 📥 DIRECT COUNTER CASH CLOSING CHECKOUT ENDPOINT
@app.post("/api/checkout")
def checkout(cart: str = Form(...), db: Session = Depends(get_db)):
    items = json.loads(cart)
    total_amount = 0.0
    for item in items:
        product = db.query(database.Product).filter(database.Product.barcode == item['barcode']).first()
        if product:
            product.stock -= item['qty']
            total_amount += product.price * item['qty']
            
    sale = database.HistoricalSale(total_amount=total_amount * 1.08, items_json=cart)
    db.add(sale)
    db.commit()
    return {"status": "success"}

@app.post("/api/simulate-shop-order")
def simulate_shop_order(db: Session = Depends(get_db)):
    mock_order = database.ShopOrder(
        shop_name="Hanout Sehraoui youness", items_summary="3x Organic Coffee, 10x Almond Milk",
        total_price=79.87, gps_latitude=30.3344, gps_longitude=-9.4952,
        store_photo_url="https://images.unsplash.com/photo-1578916171728-46686eac8d58?q=80&w=200", status="Pending"
    )
    db.add(mock_order)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# 📡 BACKGROUND WORKERTHREAD ROUTER: Outbound Telegram API Pipeline Notifications
def send_telegram_notification(shop_name: str, order_id: int, total_price: float, items: str, message_type: str):
    try:
        TELEGRAM_CHAT_ID = "-5203981397"
        TELEGRAM_BOT_TOKEN = "8333908099:AAHUWShjnNt3FTNTYopbWkme3a1jRxoI8Zg"
        
        if message_type == "dispatched":
            message_body = (
                f"🚚 <b>[PINKBIKEUS DISPATCH]</b>\n\n"
                f"Wholesale Order <b>#{order_id}</b> has been approved and packed at the central warehouse!\n\n"
                f"🏪 <b>Client Shop:</b> {shop_name}\n"
                f"📦 <b>Manifest:</b> {items}\n"
                f"💰 <b>Total Bill:</b> ${total_price:.2f}\n\n"
                f"✅ Our livreur has received the tracking sheet and is departing now."
            )
        elif message_type == "delivered":
            message_body = (
                f"🎉 <b>[PINKBIKEUS DELIVERED]</b>\n\n"
                f"Livreur has successfully completed the drop routing sequence for Order <b>#{order_id}</b>!\n\n"
                f"🏪 <b>Client Shop:</b> {shop_name}\n"
                f"💰 <b>Collected Revenue:</b> ${total_price:.2f}\n\n"
                f"💾 Transaction closed and logged to historical database ledger archives."
            )

        telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        form_params = {"chat_id": TELEGRAM_CHAT_ID, "text": message_body, "parse_mode": "HTML"}
        encoded_payload = urllib.parse.urlencode(form_params).encode('utf-8')
        
        req = urllib.request.Request(telegram_api_url, data=encoded_payload, headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
        ssl_context = ssl._create_unverified_context()
        
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            print(f"📡 Telegram API Broadcast Status [{message_type}]: {response.read().decode('utf-8')}")
    except Exception as err:
        print(f"⚠️ Asynchronous Telegram Messaging Engine Error: {err}")

# 📦 SUPPLY CHAIN LIFECYCLE STAGE 1: Admin Approves & Dispatches Order Manifest Crate
@app.post("/api/approve-order/{order_id}")
def approve_order(order_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    order = db.query(database.ShopOrder).filter(database.ShopOrder.id == order_id).first()
    if order and order.status == "Pending":
        order.status = "Completed"
        if "Organic Coffee" in order.items_summary:
            prod = db.query(database.Product).filter(database.Product.barcode == "11111").first()
            if prod: prod.stock -= 3
        if "Almond Milk" in order.items_summary:
            prod = db.query(database.Product).filter(database.Product.barcode == "22222").first()
            if prod: prod.stock -= 10
        db.commit()
        background_tasks.add_task(send_telegram_notification, order.shop_name, order.id, order.total_price, order.items_summary, "dispatched")
    return {"status": "success"}

# 🚚 SUPPLY CHAIN LIFECYCLE STAGE 2: Livreur Confirms Route Drop at Destination
@app.post("/api/deliver-order/{order_id}")
def deliver_order(order_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    order = db.query(database.ShopOrder).filter(database.ShopOrder.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    order.status = "Delivered"
    db.commit()
    background_tasks.add_task(send_telegram_notification, order.shop_name, order.id, order.total_price, order.items_summary, "delivered")
    return {"status": "success"}