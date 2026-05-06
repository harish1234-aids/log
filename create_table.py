from app import app, db
from models import StaffAllocation
with app.app_context():
    try:
        StaffAllocation.__table__.create(db.engine)
        print("StaffAllocation table created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")
