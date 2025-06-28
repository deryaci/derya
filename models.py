from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    grades = db.relationship('Grade', backref='student', lazy=True, foreign_keys='Grade.student_id')
    assignments = db.relationship('Assignment', backref='student', lazy=True, foreign_keys='Assignment.student_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Relationships
    grades = db.relationship('Grade', backref='subject', lazy=True)
    assignments = db.relationship('Assignment', backref='subject', lazy=True)
    
    def __repr__(self):
        return f'<Subject {self.name}>'

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    grade = db.Column(db.Float, nullable=False)
    exam_type = db.Column(db.String(50), nullable=False)  # 'midterm', 'final', 'quiz', etc.
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    file_path = db.Column(db.String(500))  # Path to uploaded PDF file
    original_filename = db.Column(db.String(255))  # Original filename
    
    def __repr__(self):
        return f'<Grade {self.grade} for {self.student.username}>'

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'overdue'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    file_path = db.Column(db.String(500))  # Path to uploaded file
    original_filename = db.Column(db.String(255))  # Original filename
    
    def __repr__(self):
        return f'<Assignment {self.title}>'

def initialize_default_data():
    """Initialize default users and subjects if they don't exist"""
    
    # Check if users already exist
    if User.query.first() is None:
        # Create default teacher
        teacher = User(
            username='deryam',
            role='teacher',
            full_name='Derya Öğretmen',
            email='deryam@example.com'
        )
        teacher.set_password('1234')
        db.session.add(teacher)
        
        # Create default students
        student1 = User(
            username='student1',
            role='student',
            full_name='Öğrenci Bir',
            email='student1@example.com'
        )
        student1.set_password('1111')
        db.session.add(student1)
        
        student2 = User(
            username='student2',
            role='student',
            full_name='Öğrenci İki',
            email='student2@example.com'
        )
        student2.set_password('2222')
        db.session.add(student2)
        
        db.session.commit()
    
    # Check if subjects already exist
    if Subject.query.first() is None:
        # Create default subjects
        math = Subject(name='Matematik', description='Matematik dersi')
        science = Subject(name='Fen Bilgisi', description='Fen bilgisi dersi')
        turkish = Subject(name='Türkçe', description='Türkçe dersi')
        
        db.session.add(math)
        db.session.add(science)
        db.session.add(turkish)
        db.session.commit()
        
        # Add some sample grades and assignments
        student1 = User.query.filter_by(username='student1').first()
        student2 = User.query.filter_by(username='student2').first()
        
        if student1 and student2:
            # Sample grades
            grade1 = Grade(student_id=student1.id, subject_id=math.id, grade=85, exam_type='Ara Sınav')
            grade2 = Grade(student_id=student1.id, subject_id=science.id, grade=90, exam_type='Quiz')
            grade3 = Grade(student_id=student2.id, subject_id=math.id, grade=70, exam_type='Ara Sınav')
            grade4 = Grade(student_id=student2.id, subject_id=science.id, grade=75, exam_type='Quiz')
            
            db.session.add(grade1)
            db.session.add(grade2)
            db.session.add(grade3)
            db.session.add(grade4)
            
            # Sample assignments
            from datetime import datetime, timedelta
            
            assignment1 = Assignment(
                title='Matematik Ödevi 1',
                description='Cebir konusu üzerine ödevler',
                subject_id=math.id,
                student_id=student1.id,
                due_date=datetime.utcnow() + timedelta(days=7)
            )
            
            assignment2 = Assignment(
                title='Fen Bilgisi Projesi',
                description='Güneş sistemi hakkında araştırma projesi',
                subject_id=science.id,
                student_id=student1.id,
                due_date=datetime.utcnow() + timedelta(days=14)
            )
            
            assignment3 = Assignment(
                title='Matematik Ödevi 2',
                description='Geometri problemleri',
                subject_id=math.id,
                student_id=student2.id,
                due_date=datetime.utcnow() + timedelta(days=5)
            )
            
            db.session.add(assignment1)
            db.session.add(assignment2)
            db.session.add(assignment3)
            
            db.session.commit()
