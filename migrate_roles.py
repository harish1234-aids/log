import os
from app import app, db
from models import User, News
from sqlalchemy import text

def migrate():
    with app.app_context():
        # 1. Add target_role column to news table if it doesn't exist
        try:
            db.session.execute(text("ALTER TABLE news ADD COLUMN target_role VARCHAR(20) DEFAULT 'All'"))
            db.session.commit()
            print("Added target_role column to news table.")
        except Exception as e:
            db.session.rollback()
            print(f"Column target_role might already exist: {e}")

        # 2. Migrate existing master_admin to hod
        admins = User.query.filter_by(role='master_admin').all()
        for admin in admins:
            admin.role = 'hod'
            if not admin.department:
                admin.department = 'CSE' # Default department for migrated admins
            print(f"Migrated admin '{admin.username}' to HOD (Department: {admin.department}).")
        
        # 3. Create Principal account if it doesn't exist
        principal = User.query.filter_by(role='principal').first()
        if not principal:
            principal = User(username='principal', role='principal')
            principal.set_password('principal123')
            db.session.add(principal)
            print("Created Principal account: principal / principal123")
        
        db.session.commit()
        print("Migration completed successfully.")

if __name__ == '__main__':
    migrate()
