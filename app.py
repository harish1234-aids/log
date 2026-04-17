import os
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, extract
from datetime import datetime
from models import db, User, Student, Attendance

app = Flask(__name__)
# Configurations
app.config['SECRET_KEY'] = 'supersecretkey123'
base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(base_dir, "attendance.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload config
UPLOAD_FOLDER = os.path.join(base_dir, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'master_admin':
            return redirect(url_for('manage_staff'))
        elif current_user.role == 'staff':
            return redirect(url_for('admin_dashboard')) # Mark attendance default
        else:
            return redirect(url_for('student_home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- MASTER ADMIN ONLY ROUTES ---
@app.route('/manage_staff', methods=['GET', 'POST'])
@login_required
def manage_staff():
    if current_user.role != 'master_admin':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists!', 'danger')
            else:
                staff = User(username=username, role='staff')
                staff.set_password(password)
                db.session.add(staff)
                db.session.commit()
                flash('Staff Admin created successfully!', 'success')
                
        elif action == 'delete':
            user_id = request.form.get('user_id')
            user_to_delete = User.query.get(user_id)
            if user_to_delete and user_to_delete.role == 'staff':
                db.session.delete(user_to_delete)
                db.session.commit()
                flash('Staff deleted!', 'success')
                
        elif action == 'update':
            user_id = request.form.get('user_id')
            new_username = request.form.get('username')
            new_password = request.form.get('password') # optional

            staff_user = User.query.get(user_id)
            if staff_user and staff_user.role == 'staff':
                existing_user = User.query.filter_by(username=new_username).first()
                if existing_user and existing_user.id != staff_user.id:
                    flash('Username already taken.', 'danger')
                else:
                    staff_user.username = new_username
                    if new_password:
                        staff_user.set_password(new_password)
                    db.session.commit()
                    flash('Staff updated successfully!', 'success')

    staff_members = User.query.filter_by(role='staff').all()
    return render_template('manage_staff.html', staff_members=staff_members)


# --- STAFF & MASTER ADMIN ROUTES (CRUD Data) ---
@app.route('/manage_students', methods=['GET', 'POST'])
@login_required
def manage_students():
    if current_user.role not in ['master_admin', 'staff']:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name')
            department = request.form.get('department')
            year = request.form.get('year')
            username = request.form.get('username')
            password = request.form.get('password')
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists!', 'danger')
            else:
                try:
                    student = Student(name=name, department=department, year=int(year))
                    db.session.add(student)
                    db.session.commit()
                    
                    user = User(username=username, role='student', department=department, year=int(year), student_id=student.id)
                    user.set_password(password)
                    db.session.add(user)
                    db.session.commit()
                    
                    flash('Student added successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'An error occurred: {str(e)}', 'danger')
                    
        elif action == 'delete':
            student_id = request.form.get('student_id')
            student = Student.query.get(student_id)
            if student:
                # Due to cascade delete, this will remove attendance records as well
                db.session.delete(student)
                db.session.commit()
                flash('Student and records deleted.', 'success')
                
        elif action == 'update':
            student_id = request.form.get('student_id')
            name = request.form.get('name')
            department = request.form.get('department')
            year = request.form.get('year')
            username = request.form.get('username')
            password = request.form.get('password')

            student = Student.query.get(student_id)
            if student:
                user = student.user_account
                if username and user.username != username:
                    if User.query.filter_by(username=username).first():
                        flash('Username already taken by another user!', 'danger')
                        return redirect(url_for('manage_students'))
                    user.username = username
                    
                student.name = name
                student.department = department
                student.year = int(year)
                
                if user:
                    user.department = department
                    user.year = int(year)
                    if password:
                        user.set_password(password)

                db.session.commit()
                
                # Update attendance tags to stay visually consistent
                Attendance.query.filter_by(student_id=student.id).update({
                    'department': department,
                    'year': int(year)
                })
                db.session.commit()

                flash('Student updated successfully!', 'success')
            
        return redirect(url_for('manage_students'))

    # Retrieve Filter Arguments
    filter_dept = request.args.get('dept', 'All')
    filter_year = request.args.get('year', 'All')
    
    query = Student.query
    if filter_dept != 'All':
        query = query.filter(Student.department == filter_dept)
    if filter_year != 'All' and filter_year.isdigit():
        query = query.filter(Student.year == int(filter_year))
        
    students = query.all()
    
    departments = [d[0] for d in Student.query.with_entities(Student.department).distinct().all() if d[0]]
    years = [y[0] for y in Student.query.with_entities(Student.year).distinct().order_by(Student.year).all() if y[0]]
    if not departments: departments = ['CSE', 'IT', 'ECE', 'MECH']
    if not years: years = [1, 2, 3, 4]

    return render_template('manage_students.html', students=students, 
                           departments=departments, years=years,
                           filter_dept=filter_dept, filter_year=filter_year)


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    # Mark Attendance page
    if current_user.role not in ['master_admin', 'staff']:
        return redirect(url_for('index'))
        
    departments = [d[0] for d in db.session.query(Student.department).distinct().all()]
    years = [y[0] for y in db.session.query(Student.year).distinct().all()]
    
    students = []
    selected_date = None
    selected_dept = None
    selected_year = None
    selected_period = None
    existing_attendance = {}
    
    if request.method == 'POST':
        action = request.form.get('action')
        selected_date = request.form.get('date')
        selected_dept = request.form.get('department')
        selected_year_str = request.form.get('year')
        selected_period_str = request.form.get('period')
        
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash('Invalid date format', 'danger')
            return render_template('attend-admin.html', departments=departments, years=years, students=[], date=selected_date)
            
        if selected_year_str and selected_year_str.isdigit():
            selected_year = int(selected_year_str)
        if selected_period_str and selected_period_str.isdigit():
            selected_period = int(selected_period_str)
            
        if action == 'load':
            if selected_dept and selected_year and selected_period:
                students = Student.query.filter_by(department=selected_dept, year=selected_year).all()
                
                # Load existing attendance
                att_records = Attendance.query.filter_by(
                    department=selected_dept, year=selected_year, date=date_obj, period=selected_period
                ).all()
                
                for record in att_records:
                    existing_attendance[record.student_id] = record.status
                    
        elif action == 'submit':
            if selected_dept and selected_year and selected_period:
                students = Student.query.filter_by(department=selected_dept, year=selected_year).all()
                for student in students:
                    status = request.form.get(f'attendance_{student.id}')
                    is_present = status == 'on' 

                    attendance_record = Attendance.query.filter_by(
                        student_id=student.id, date=date_obj, period=selected_period
                    ).first()
                    
                    if attendance_record:
                        attendance_record.status = is_present
                    else:
                        new_record = Attendance(
                            student_id=student.id,
                            date=date_obj,
                            period=selected_period,
                            status=is_present,
                            department=selected_dept,
                            year=selected_year
                        )
                        db.session.add(new_record)
                
                db.session.commit()
                flash(f'Attendance saved for Period {selected_period}!', 'success')
                
                # Reload existing
                att_records = Attendance.query.filter_by(
                    department=selected_dept, year=selected_year, date=date_obj, period=selected_period
                ).all()
                for record in att_records:
                    existing_attendance[record.student_id] = record.status

    from models import TimetableConfig, Feedback, SharedFile
    config = TimetableConfig.query.first()
    timetable_blocks = []
    if config and config.layout_data:
        import json
        try:
            timetable_blocks = json.loads(config.layout_data)
        except:
            pass
            
    feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    from models import News
    news_posts = News.query.order_by(News.timestamp.desc()).all()
    shared_files = SharedFile.query.order_by(SharedFile.timestamp.desc()).all()

    return render_template('attend-admin.html', departments=departments, years=years, 
                           students=students, selected_date=selected_date,
                           selected_dept=selected_dept, selected_year=selected_year,
                           selected_period=selected_period, existing_attendance=existing_attendance,
                           timetable_blocks=timetable_blocks, feedbacks=feedbacks,
                           news_posts=news_posts, shared_files=shared_files)

@app.route('/delete_feedback/<int:fb_id>', methods=['POST'])
@login_required
def delete_feedback(fb_id):
    if current_user.role not in ['master_admin', 'staff']:
        return redirect(url_for('index'))
    from models import Feedback
    fb = Feedback.query.get(fb_id)
    if fb:
        db.session.delete(fb)
        db.session.commit()
        flash('Feedback deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/post_news', methods=['POST'])
@login_required
def post_news():
    if current_user.role not in ['master_admin', 'staff']:
        return redirect(url_for('index'))
    from models import News
    title = request.form.get('title')
    content = request.form.get('content')
    target_dept = request.form.get('target_dept') or 'All'
    target_year = request.form.get('target_year') or 'All'
    if title and content:
        n = News(author_id=current_user.id, title=title, content=content, target_dept=target_dept, target_year=target_year)
        db.session.add(n)
        db.session.commit()
        flash('News broadcast published successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_news/<int:news_id>', methods=['POST'])
@login_required
def delete_news(news_id):
    if current_user.role not in ['master_admin', 'staff']:
        return redirect(url_for('index'))
    from models import News
    n = News.query.get(news_id)
    if n and (n.author_id == current_user.id or current_user.role == 'master_admin'):
        db.session.delete(n)
        db.session.commit()
        flash('Announcement deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/timetable_admin', methods=['GET', 'POST'])
@login_required
def timetable_admin():
    if current_user.role != 'master_admin':
        return redirect(url_for('index'))
        
    from models import TimetableConfig
    config = TimetableConfig.query.first()
    if not config:
        config = TimetableConfig()
        db.session.add(config)
        db.session.commit()
        
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'generate':
            config.total_days = int(request.form.get('total_days') or 5)
            config.total_periods = int(request.form.get('total_periods') or 6)
            config.break_after = int(request.form.get('break_after') or 2)
            config.lunch_after = int(request.form.get('lunch_after') or 4)
            
            config.layout_data = None
            db.session.commit()
            
        elif action == 'save_names':
            layout_data = request.form.get('layout_data')
            if layout_data:
                config.layout_data = layout_data
                db.session.commit()
                flash('Timetable structures updated!', 'success')
                
    return render_template('timetable_admin.html', config=config)

@app.route('/analytics')
@login_required
def analytics():
    if current_user.role not in ['master_admin', 'staff']:
        return redirect(url_for('index'))
        
    date_str = request.args.get('date', datetime.today().strftime('%Y-%m-%d'))
    try:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        report_date = datetime.today().date()
        
    # --- Data for Graph 1: Period-wise Attendance Graph of Total Students ---
    # Fetch total students marked present per period on the selected date
    period_stats = db.session.query(
        Attendance.period, func.count(Attendance.id).label('total_present')
    ).filter(
        Attendance.date == report_date,
        Attendance.status == True
    ).group_by(Attendance.period).order_by(Attendance.period).all()
    
    period_labels = [f"Period {p[0]}" for p in period_stats]
    period_data = [p[1] for p in period_stats]

    # --- Data for Graph 2: Monthly Attendance (Individual VS Overall) ---
    current_month = report_date.month
    current_year = report_date.year

    # Get overall monthly stats
    total_monthly_marked = Attendance.query.filter(
        extract('month', Attendance.date) == current_month,
        extract('year', Attendance.date) == current_year
    ).count()

    total_monthly_present = Attendance.query.filter(
        extract('month', Attendance.date) == current_month,
        extract('year', Attendance.date) == current_year,
        Attendance.status == True
    ).count()

    overall_monthly_percentage = 0
    if total_monthly_marked > 0:
        overall_monthly_percentage = round((total_monthly_present / total_monthly_marked) * 100, 2)

    # Individual Student Table Data (Monthly)
    students = Student.query.all()
    monthly_student_stats = []
    
    for s in students:
        s_total = Attendance.query.filter_by(student_id=s.id).filter(
            extract('month', Attendance.date) == current_month,
            extract('year', Attendance.date) == current_year
        ).count()
        s_present = Attendance.query.filter_by(student_id=s.id, status=True).filter(
            extract('month', Attendance.date) == current_month,
            extract('year', Attendance.date) == current_year
        ).count()
        
        pct = round((s_present / s_total) * 100, 2) if s_total > 0 else 0
        monthly_student_stats.append({
            'name': s.name,
            'department': s.department,
            'total_periods': s_total,
            'present_periods': s_present,
            'percentage': pct
        })
        
    # Prepare top 5 for chart or just a subset
    top_students = sorted(monthly_student_stats, key=lambda x: x['percentage'], reverse=True)[:10]
    student_labels = [s['name'] for s in top_students]
    student_data = [s['percentage'] for s in top_students]

    return render_template('analytics.html', 
                           report_date=report_date,
                           period_labels=period_labels,
                           period_data=period_data,
                           overall_monthly_percentage=overall_monthly_percentage,
                           monthly_student_stats=monthly_student_stats,
                           student_labels=student_labels,
                           student_data=student_data)

# --- STUDENT ROUTES ---
@app.route('/home', methods=['GET', 'POST'])
@login_required
def student_home():
    if current_user.role != 'student':
        return redirect(url_for('index'))
        
    from models import Feedback, News
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            new_fb = Feedback(student_id=current_user.student_id, message=message)
            db.session.add(new_fb)
            db.session.commit()
            flash('Your feedback was safely submitted to the administration!', 'success')
            return redirect(url_for('student_home'))
            
    from sqlalchemy import or_
    latest_news = News.query.filter(
        or_(News.target_dept == 'All', News.target_dept == current_user.department),
        or_(News.target_year == 'All', News.target_year == str(current_user.year))
    ).order_by(News.timestamp.desc()).limit(10).all()

    from models import SharedFile
    student_files = SharedFile.query.filter(
        or_(SharedFile.target_dept == 'All', SharedFile.target_dept == current_user.department),
        or_(SharedFile.target_year == 'All', SharedFile.target_year == str(current_user.year))
    ).order_by(SharedFile.timestamp.desc()).all()
        
    current_month = datetime.today().month
    current_year = datetime.today().year
    
    total_periods = Attendance.query.filter_by(student_id=current_user.student_id).filter(
        extract('month', Attendance.date) == current_month,
        extract('year', Attendance.date) == current_year
    ).count()
    
    present_periods = Attendance.query.filter_by(student_id=current_user.student_id, status=True).filter(
        extract('month', Attendance.date) == current_month,
        extract('year', Attendance.date) == current_year
    ).count()
    
    monthly_percentage = 0
    if total_periods > 0:
        monthly_percentage = round((present_periods / total_periods) * 100, 2)
        
    return render_template('home.html', monthly_percentage=monthly_percentage,
                           latest_news=latest_news, student_files=student_files)

@app.route('/attendance')
@login_required
def student_attendance_list():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    # Dates where any attendance was recorded for this user
    query_dates = db.session.query(Attendance.date).filter_by(
        student_id=current_user.student_id
    ).distinct().order_by(Attendance.date.desc()).all()
    
    marked_dates = [d[0] for d in query_dates]
    return render_template('attendance.html', dates=marked_dates)

@app.route('/attendance/view')
@login_required
def student_attendance_view():
    if current_user.role != 'student':
        return redirect(url_for('index'))
        
    date_str = request.args.get('date')
    if not date_str:
        return redirect(url_for('student_attendance_list'))
        
    try:
        view_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return redirect(url_for('student_attendance_list'))
        
    # Get period-wise attendance for exactly this student on this day
    attendances_record = Attendance.query.filter_by(
        student_id=current_user.student_id,
        date=view_date
    ).order_by(Attendance.period).all()
        
    return render_template('attendance_view.html', attendances=attendances_record, date=view_date)

@app.route('/student_timetable')
@login_required
def student_timetable():
    if current_user.role != 'student':
        return redirect(url_for('index'))
        
    from models import TimetableConfig
    config = TimetableConfig.query.first()
    timetable_blocks = []
    if config and config.layout_data:
        import json
        try:
            timetable_blocks = json.loads(config.layout_data)
        except:
            pass
            
    return render_template('timetable_student.html', timetable_blocks=timetable_blocks)

# --- INTERNAL MARKS SYSTEM ---

@app.route('/manage_marks', methods=['GET', 'POST'])
@login_required
def manage_marks():
    if current_user.role not in ['master_admin', 'staff']:
        return redirect(url_for('index'))
        
    from models import InternalMark
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            student_id = request.form.get('student_id')
            subject = request.form.get('subject')
            exam_type = request.form.get('exam_type')
            marks_obtained = request.form.get('marks_obtained')
            max_marks = request.form.get('max_marks', 100)
            
            im = InternalMark(student_id=student_id, author_id=current_user.id, subject=subject, exam_type=exam_type, marks_obtained=marks_obtained, max_marks=max_marks)
            db.session.add(im)
            db.session.commit()
            flash('Marks successfully recorded!', 'success')
        elif action == 'delete':
            mark_id = request.form.get('mark_id')
            im = InternalMark.query.get(mark_id)
            if im and (current_user.role == 'master_admin' or im.author_id == current_user.id):
                db.session.delete(im)
                db.session.commit()
                flash('Mark record deleted.', 'success')
        return redirect(url_for('manage_marks'))
        
    # GET Filter Arguments
    filter_dept = request.args.get('dept', 'All')
    filter_year = request.args.get('year', 'All')
    
    q_students = Student.query
    if filter_dept != 'All':
        q_students = q_students.filter(Student.department == filter_dept)
    if filter_year != 'All' and filter_year.isdigit():
        q_students = q_students.filter(Student.year == int(filter_year))
    students = q_students.all()
    
    q_marks = InternalMark.query.join(Student)
    if filter_dept != 'All':
       q_marks = q_marks.filter(Student.department == filter_dept)
    if filter_year != 'All' and filter_year.isdigit():
       q_marks = q_marks.filter(Student.year == int(filter_year))
           
    marks = q_marks.order_by(InternalMark.timestamp.desc()).all()
    
    departments = [d[0] for d in Student.query.with_entities(Student.department).distinct().all() if d[0]]
    years = [y[0] for y in Student.query.with_entities(Student.year).distinct().order_by(Student.year).all() if y[0]]
    if not departments: departments = ['CSE', 'IT', 'ECE', 'MEECH']
    if not years: years = [1, 2, 3, 4]
    
    return render_template('manage_marks.html', students=students, marks=marks, 
                           departments=departments, years=years, 
                           filter_dept=filter_dept, filter_year=filter_year)

@app.route('/student_marks')
@login_required
def student_marks():
    if current_user.role != 'student':
        return redirect(url_for('index'))
        
    from models import InternalMark
    marks = InternalMark.query.filter_by(student_id=current_user.student_id).all()
    
    return render_template('student_marks.html', marks=marks)

# ── CHANGE CREDENTIALS ──

def _cred_redirect():
    """Safe redirect back to the caller's dashboard — works on mobile where Referer header may be absent."""
    if current_user.role == 'master_admin':
        return url_for('manage_staff')
    return url_for('admin_dashboard')

@app.route('/change_credentials', methods=['POST'])
@login_required
def change_credentials():
    if current_user.role not in ['master_admin', 'staff']:
        return redirect(url_for('index'))

    new_username     = request.form.get('new_username', '').strip()
    new_password     = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not new_username:
        flash('Username cannot be empty.', 'danger')
        return redirect(_cred_redirect())

    # Check username uniqueness (ignore current user's own record)
    existing = User.query.filter_by(username=new_username).first()
    if existing and existing.id != current_user.id:
        flash('That username is already taken. Please choose another.', 'danger')
        return redirect(_cred_redirect())

    # Check passwords match (only if a new password was supplied)
    if new_password:
        if new_password != confirm_password:
            flash('Passwords do not match. No changes were saved.', 'danger')
            return redirect(_cred_redirect())
        current_user.set_password(new_password)

    current_user.username = new_username
    try:
        db.session.commit()
        flash('Account credentials updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while saving: {str(e)}', 'danger')

    return redirect(_cred_redirect())


# ── FILE BROADCAST ROUTES ──

@app.route('/send_file', methods=['POST'])
@login_required
def send_file_broadcast():
    if current_user.role not in ['master_admin', 'staff']:
        return redirect(url_for('index'))

    from models import SharedFile
    title = request.form.get('title', '').strip()
    target_dept = request.form.get('target_dept', 'All')
    target_year = request.form.get('target_year', 'All')
    file = request.files.get('shared_file')

    if not title:
        flash('Please provide a title for the file.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if not file or file.filename == '':
        flash('No file selected. Please choose a PDF or image.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if not allowed_file(file.filename):
        flash('Invalid file type. Allowed: PDF, PNG, JPG, JPEG, GIF, WEBP.', 'danger')
        return redirect(url_for('admin_dashboard'))

    ext = file.filename.rsplit('.', 1)[1].lower()
    file_type = 'pdf' if ext == 'pdf' else 'image'
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(save_path)

    sf = SharedFile(
        author_id=current_user.id,
        title=title,
        filename=unique_name,
        original_name=file.filename,
        file_type=file_type,
        target_dept=target_dept,
        target_year=target_year
    )
    db.session.add(sf)
    db.session.commit()
    flash(f'File "{title}" sent successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/delete_shared_file/<int:file_id>', methods=['POST'])
@login_required
def delete_shared_file(file_id):
    if current_user.role not in ['master_admin', 'staff']:
        return redirect(url_for('index'))

    from models import SharedFile
    sf = SharedFile.query.get(file_id)
    if sf and (current_user.role == 'master_admin' or sf.author_id == current_user.id):
        # Remove file from disk
        disk_path = os.path.join(app.config['UPLOAD_FOLDER'], sf.filename)
        if os.path.exists(disk_path):
            os.remove(disk_path)
        db.session.delete(sf)
        db.session.commit()
        flash('File deleted successfully.', 'success')
    else:
        flash('You do not have permission to delete this file.', 'danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Initialize master admin dynamically safely
        master = User.query.filter_by(username='admin').first()
        if not master:
            master = User(username='admin', role='master_admin')
            master.set_password('admin')
            db.session.add(master)
            db.session.commit()
    app.run(debug=True, port=5000)
