from flask import render_template, request, redirect, url_for, session, flash, send_from_directory
from app import app, db
from models import User, Subject, Grade, Assignment
from datetime import datetime
from werkzeug.utils import secure_filename
import os

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['full_name'] = user.full_name
            
            if user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre!', 'error')
    
    return render_template('login.html')

@app.route('/teacher/dashboard')
def teacher_dashboard():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    # Get statistics
    total_students = User.query.filter_by(role='student').count()
    total_subjects = Subject.query.count()
    total_assignments = Assignment.query.count()
    
    # Get recent grades
    recent_grades = db.session.query(Grade, User, Subject).join(
        User, Grade.student_id == User.id
    ).join(
        Subject, Grade.subject_id == Subject.id
    ).order_by(Grade.date_recorded.desc()).limit(5).all()
    
    # Get pending assignments
    pending_assignments = db.session.query(Assignment, User, Subject).join(
        User, Assignment.student_id == User.id
    ).join(
        Subject, Assignment.subject_id == Subject.id
    ).filter(Assignment.status == 'pending').order_by(Assignment.due_date).limit(5).all()
    
    return render_template('teacher_dashboard.html',
                         total_students=total_students,
                         total_subjects=total_subjects,
                         total_assignments=total_assignments,
                         recent_grades=recent_grades,
                         pending_assignments=pending_assignments)

@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get student's grades
    grades = db.session.query(Grade, Subject).join(
        Subject, Grade.subject_id == Subject.id
    ).filter(Grade.student_id == user_id).order_by(Grade.date_recorded.desc()).all()
    
    # Get student's assignments
    assignments = db.session.query(Assignment, Subject).join(
        Subject, Assignment.subject_id == Subject.id
    ).filter(Assignment.student_id == user_id).order_by(Assignment.due_date).all()
    
    # Calculate average grade
    total_grades = [grade.grade for grade, _ in grades]
    average_grade = sum(total_grades) / len(total_grades) if total_grades else 0
    
    return render_template('student_dashboard.html',
                         grades=grades,
                         assignments=assignments,
                         average_grade=round(average_grade, 2),
                         current_date=datetime.utcnow())

@app.route('/teacher/manage-grades', methods=['GET', 'POST'])
def manage_grades():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject_id = request.form['subject_id']
        try:
            grade_str = request.form['grade'].strip().lower()
            if grade_str in ['nan', 'inf', '-inf', '+inf']:
                flash('Geçersiz not değeri!', 'error')
                return redirect(url_for('manage_grades'))
            grade = float(request.form['grade'])
            if not (0 <= grade <= 100):  # Assuming grades are 0-100
                flash('Not 0-100 arasında olmalıdır!', 'error')
                return redirect(url_for('manage_grades'))
        except ValueError:
            flash('Geçersiz not değeri!', 'error')
            return redirect(url_for('manage_grades'))
        exam_type = request.form['exam_type']
        notes = request.form.get('notes', '')
        
        # Handle file upload
        file_path = None
        original_filename = None
        if 'exam_file' in request.files:
            file = request.files['exam_file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Create unique filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                original_filename = file.filename
        
        new_grade = Grade(
            student_id=student_id,
            subject_id=subject_id,
            grade=grade,
            exam_type=exam_type,
            notes=notes,
            file_path=filename if file_path else None,
            original_filename=original_filename
        )
        
        db.session.add(new_grade)
        db.session.commit()
        flash('Not başarıyla eklendi!', 'success')
        return redirect(url_for('manage_grades'))
    
    # Get all students and subjects for the form
    students = User.query.filter_by(role='student').all()
    subjects = Subject.query.all()
    
    # Get all grades with student and subject info
    grades = db.session.query(Grade, User, Subject).join(
        User, Grade.student_id == User.id
    ).join(
        Subject, Grade.subject_id == Subject.id
    ).order_by(Grade.date_recorded.desc()).all()
    
    return render_template('manage_grades.html',
                         students=students,
                         subjects=subjects,
                         grades=grades)

@app.route('/teacher/manage-assignments', methods=['GET', 'POST'])
def manage_assignments():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        subject_id = request.form['subject_id']
        student_id = request.form['student_id']
        due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d')
        
        new_assignment = Assignment(
            title=title,
            description=description,
            subject_id=subject_id,
            student_id=student_id,
            due_date=due_date
        )
        
        # Handle file upload if provided
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Create unique filename with timestamp
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
                unique_filename = timestamp + filename
                
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                # Update assignment with file info
                new_assignment.file_path = f'uploads/{unique_filename}'
                new_assignment.original_filename = filename
        
        db.session.add(new_assignment)
        db.session.commit()
        flash('Ödev başarıyla eklendi!', 'success')
        return redirect(url_for('manage_assignments'))
    
    # Get all students and subjects for the form
    students = User.query.filter_by(role='student').all()
    subjects = Subject.query.all()
    
    # Get all assignments with student and subject info
    assignments = db.session.query(Assignment, User, Subject).join(
        User, Assignment.student_id == User.id
    ).join(
        Subject, Assignment.subject_id == Subject.id
    ).order_by(Assignment.due_date).all()
    
    return render_template('manage_assignments.html',
                         students=students,
                         subjects=subjects,
                         assignments=assignments,
                         current_date=datetime.utcnow())

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'doc', 'docx', 'txt'})

@app.route('/assignment/<int:assignment_id>/complete', methods=['POST'])
def complete_assignment(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if the assignment belongs to the current student
    if session.get('role') == 'student' and assignment.student_id != session['user_id']:
        flash('Bu ödevi tamamlama yetkiniz yok!', 'error')
        return redirect(url_for('student_dashboard'))
    
    assignment.status = 'completed'
    assignment.completed_at = datetime.utcnow()
    db.session.commit()
    
    flash('Ödev tamamlandı olarak işaretlendi!', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/assignment/<int:assignment_id>/upload', methods=['POST'])
def upload_assignment_file(assignment_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash('Bu işlem için yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    assignment = Assignment.query.get_or_404(assignment_id)
    
    if 'file' not in request.files:
        flash('Dosya seçilmedi!', 'error')
        return redirect(url_for('manage_assignments'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('Dosya seçilmedi!', 'error')
        return redirect(url_for('manage_assignments'))
    
    if file and allowed_file(file.filename):
        # Remove old file if exists
        if assignment.file_path:
            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], assignment.file_path.split('/')[-1])
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        filename = secure_filename(file.filename)
        # Create unique filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
        unique_filename = timestamp + filename
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Update assignment with file info
        assignment.file_path = f'uploads/{unique_filename}'
        assignment.original_filename = filename
        
        db.session.commit()
        
        flash('Ödev dosyası başarıyla yüklendi!', 'success')
    else:
        flash('Sadece PDF, DOC, DOCX ve TXT dosyaları yükleyebilirsiniz!', 'error')
    
    return redirect(url_for('manage_assignments'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/grade/<int:grade_id>/download')
def download_grade_file(grade_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    grade = Grade.query.get_or_404(grade_id)
    
    # Check permissions - teachers can see all, students can only see their own
    if session.get('role') == 'student' and grade.student_id != session['user_id']:
        flash('Bu dosyayı görme yetkiniz yok!', 'error')
        return redirect(url_for('student_dashboard'))
    
    if not grade.file_path:
        flash('Bu not için dosya bulunmuyor!', 'error')
        return redirect(url_for('manage_grades') if session.get('role') == 'teacher' else url_for('student_dashboard'))
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], grade.file_path)

@app.route('/grade/<int:grade_id>/delete', methods=['POST'])
def delete_grade(grade_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash('Bu işlem için yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    grade = Grade.query.get_or_404(grade_id)
    student_name = grade.student.full_name
    subject_name = grade.subject.name
    
    db.session.delete(grade)
    db.session.commit()
    
    flash(f'{student_name} - {subject_name} notu başarıyla silindi!', 'success')
    return redirect(url_for('manage_grades'))

@app.route('/assignment/<int:assignment_id>/delete', methods=['POST'])
def delete_assignment(assignment_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash('Bu işlem için yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Delete uploaded file if exists
    if assignment.file_path:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], assignment.file_path.split('/')[-1])
        if os.path.exists(file_path):
            os.remove(file_path)
    
    assignment_title = assignment.title
    db.session.delete(assignment)
    db.session.commit()
    
    flash(f'"{assignment_title}" ödevi başarıyla silindi!', 'success')
    return redirect(url_for('manage_assignments'))

@app.route('/teacher/all-grades')
def view_all_grades():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    # Get all grades with pagination support
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    grades = db.session.query(Grade, User, Subject).join(
        User, Grade.student_id == User.id
    ).join(
        Subject, Grade.subject_id == Subject.id
    ).order_by(Grade.date_recorded.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('all_grades.html', grades=grades)

@app.route('/teacher/manage-students', methods=['GET', 'POST'])
def manage_students():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        email = request.form.get('email', '')
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Bu kullanıcı adı zaten kullanılıyor!', 'error')
            return redirect(url_for('manage_students'))
        
        # Create new student
        new_student = User(
            username=username,
            role='student',
            full_name=full_name,
            email=email if email else None
        )
        new_student.set_password(password)
        
        db.session.add(new_student)
        db.session.commit()
        
        flash(f'Öğrenci "{full_name}" başarıyla eklendi! (Kullanıcı adı: {username})', 'success')
        return redirect(url_for('manage_students'))
    
    # Get all students
    students = User.query.filter_by(role='student').order_by(User.created_at.desc()).all()
    
    return render_template('manage_students.html', students=students)

@app.route('/student/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash('Bu işlem için yetkiniz yok!', 'error')
        return redirect(url_for('login'))
    
    student = User.query.get_or_404(student_id)
    
    if student.role != 'student':
        flash('Sadece öğrenci hesapları silinebilir!', 'error')
        return redirect(url_for('manage_students'))
    
    student_name = student.full_name
    
    # Delete related grades and assignments
    Grade.query.filter_by(student_id=student_id).delete()
    assignments = Assignment.query.filter_by(student_id=student_id).all()
    
    # Delete uploaded files
    for assignment in assignments:
        if assignment.file_path:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], assignment.file_path.split('/')[-1])
            if os.path.exists(file_path):
                os.remove(file_path)
    
    Assignment.query.filter_by(student_id=student_id).delete()
    db.session.delete(student)
    db.session.commit()
    
    flash(f'Öğrenci "{student_name}" ve tüm verileri başarıyla silindi!', 'success')
    return redirect(url_for('manage_students'))

@app.route('/teacher/all-assignments')
def view_all_assignments():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    # Get all assignments with pagination support
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    assignments = db.session.query(Assignment, User, Subject).join(
        User, Assignment.student_id == User.id
    ).join(
        Subject, Assignment.subject_id == Subject.id
    ).order_by(Assignment.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('all_assignments.html', 
                         assignments=assignments,
                         current_date=datetime.utcnow())

@app.route('/logout')
def logout():
    session.clear()
    flash('Başarıyla çıkış yaptınız!', 'info')
    return redirect(url_for('login'))

@app.context_processor
def inject_user():
    """Make user info available in all templates"""
    if 'user_id' in session:
        return {
            'current_user': {
                'username': session.get('username'),
                'role': session.get('role'),
                'full_name': session.get('full_name')
            }
        }
    return {}
