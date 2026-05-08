from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'principal', 'hod', 'staff', 'student'
    department = db.Column(db.String(80), nullable=True) 
    year = db.Column(db.Integer, nullable=True) 
    
    # Optional linked student if role is 'student'
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    student = db.relationship('Student', backref='user_account', uselist=False, cascade='all, delete')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class StaffAllocation(db.Model):
    __tablename__ = 'staff_allocations'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department = db.Column(db.String(80), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(100), nullable=False)

    staff = db.relationship('User', backref=db.backref('allocations', lazy=True, cascade='all, delete-orphan'))

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(80), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    period = db.Column(db.Integer, nullable=False) # 1 through 8
    status = db.Column(db.Boolean, nullable=False) # True = Present, False = Absent
    department = db.Column(db.String(80), nullable=False)
    year = db.Column(db.Integer, nullable=False)

class TimetableConfig(db.Model):
    __tablename__ = 'timetable_config'
    id = db.Column(db.Integer, primary_key=True)
    total_days = db.Column(db.Integer, default=5)
    total_periods = db.Column(db.Integer, default=6)
    break_after = db.Column(db.Integer, default=2)
    lunch_after = db.Column(db.Integer, default=4)
    layout_data = db.Column(db.Text, nullable=True) # store custom names JSON
    department = db.Column(db.String(80), nullable=True)
    year = db.Column(db.Integer, nullable=True)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    target_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    student = db.relationship('Student', backref=db.backref('feedbacks', lazy=True, cascade='all, delete-orphan'))
    target_staff = db.relationship('User', foreign_keys=[target_staff_id])

class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    target_dept = db.Column(db.String(50), default='All')  # 'All', 'CSE', 'IT', etc.
    target_year = db.Column(db.String(10), default='All')  # 'All', '1', '2', '3', '4'
    target_role = db.Column(db.String(20), default='All')  # 'All', 'hod', 'staff', 'student'
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    author = db.relationship('User', backref=db.backref('news_posts', lazy=True))

class InternalMark(db.Model):
    __tablename__ = 'internal_marks'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False) # e.g., 'Internal 1', 'Model Exam'
    marks_obtained = db.Column(db.Float, nullable=False)
    max_marks = db.Column(db.Float, default=100.0)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    student = db.relationship('Student', backref=db.backref('marks', lazy=True, cascade='all, delete-orphan'))
    author = db.relationship('User', backref=db.backref('uploaded_marks', lazy=True))

class SharedFile(db.Model):
    __tablename__ = 'shared_files'
    id            = db.Column(db.Integer, primary_key=True)
    author_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title         = db.Column(db.String(200), nullable=False)
    filename      = db.Column(db.String(300), nullable=False)   # uuid-prefixed stored name
    original_name = db.Column(db.String(300), nullable=False)   # original upload filename
    file_type     = db.Column(db.String(10),  nullable=False)   # 'pdf' or 'image'
    target_dept   = db.Column(db.String(50),  default='All')    # 'All' or dept name
    target_year   = db.Column(db.String(10),  default='All')    # 'All' or '1'–'4'
    timestamp     = db.Column(db.DateTime, default=datetime.now)

    author = db.relationship('User', backref=db.backref('shared_files', lazy=True))
