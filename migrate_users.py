from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    # SQLite doesn't support ALTER TABLE ... ADD COLUMN ... IF NOT EXISTS natively in a simple way
    # But we can just try to add them and catch the error if they exist.
    columns = [
        ("name", "VARCHAR(120)"),
        ("phone", "VARCHAR(20)"),
        ("email", "VARCHAR(120)"),
        ("gender", "VARCHAR(20)")
    ]
    
    for col_name, col_type in columns:
        try:
            db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
            db.session.commit()
            print(f"Added column {col_name}")
        except Exception as e:
            db.session.rollback()
            print(f"Column {col_name} might already exist or error: {e}")
