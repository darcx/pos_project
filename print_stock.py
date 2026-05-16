import database

def check_product_by_barcode(barcode_to_find: str):
    # Open connection session
    db = database.SessionLocal()
    
    try:
        # Query only the matching barcode
        product = db.query(database.Product).filter(database.Product.barcode == barcode_to_find).first()
        
        if product:
            print(f"Barcode: {product.barcode} | Name: {product.name} | Price: ${product.price:.2f} | Stock: {product.stock}")
        else:
            print(f"⚠️ Barcode '{barcode_to_find}' not found in database.")
            
    finally:
        db.close()

if __name__ == "__main__":
    # Change this to whatever barcode you want to look up
    check_product_by_barcode("11111")