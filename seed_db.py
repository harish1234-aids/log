import sys
from app import app, db
from models import User, Student, Attendance
from datetime import datetime, timedelta
import random

def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create Principal Admin
        principal = User(username='principal', role='principal')
        principal.set_password('principal123')
        db.session.add(principal)

        # Create HODs
        hod_cse = User(username='hod_cse', role='hod', department='Computer Science')
        hod_cse.set_password('hod123')
        db.session.add(hod_cse)

        hod_it = User(username='hod_it', role='hod', department='Information Technology')
        hod_it.set_password('hod123')
        db.session.add(hod_it)

        # Create a Staff Admin
        staff = User(username='staff1', role='staff')
        staff.set_password('password')
        db.session.add(staff)

        # Add Students
        students = [
            Student(name='Alice Smith', department='Computer Science', year=1),
            Student(name='Bob Jones', department='Computer Science', year=1),
            Student(name='Charlie Brown', department='Computer Science', year=2),
            Student(name='Diana Prince', department='Information Technology', year=1),
            Student(name='Eve Adams', department='Information Technology', year=2),
        ]
        db.session.add_all(students)
        db.session.commit()

        # Create Student Users
        for s in Student.query.all():
            username = s.name.split()[0].lower()
            user = User(username=username, role='student', department=s.department, year=s.year, student_id=s.id)
            user.set_password('password')
            db.session.add(user)

        # Mock Attendance (Past 5 days, periods 1 to 4)
        for i in range(5):
            date = datetime.today().date() - timedelta(days=i)
            # skip weekends
            if date.weekday() >= 5: continue
            for s in Student.query.all():
                for p in range(1, 5): # 4 periods a day
                    att = Attendance(
                        student_id=s.id,
                        date=date,
                        period=p,
                        status=random.choice([True, True, True, False]), # 75% chance present
                        department=s.department,
                        year=s.year
                    )
                    db.session.add(att)

        db.session.commit()
        print("Database seeded! Principal: principal/principal123. HODs: hod_cse/hod123. Staff: staff1/password.")

if __name__ == '__main__':
    seed()
