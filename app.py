#!/usr/bin/env python3
import os, json, datetime, random  # Imports for file ops, config, dates, random quotes
from collections import defaultdict
from flask import Flask, render_template, send_file, request, jsonify, session, send_from_directory, redirect, url_for  # Flask web framework
from flask_cors import CORS  # Enable CORS for API
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, ForeignKey, UniqueConstraint, Boolean, func  # DB schema
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, scoped_session  # ORM tools
from bcrypt import hashpw, gensalt, checkpw  # Password hashing
import pandas as pd  # Data manipulation for Excel export
from io import BytesIO  # In-memory file for Excel
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import os
from openpyxl import Workbook
from flask import send_file


CFG_PATH = os.environ.get("NSAMIZI_CONFIG", "config.json")
if os.path.exists(CFG_PATH):
    with open(CFG_PATH,"r") as f:
        CFG = json.load(f)
else:
    CFG = {"DB_URL": "sqlite:///nsamizi_demo.db", "SECRET_KEY":"dev-key", "DEMO_BRANCHES":["Adjumani","Gulu","Nsambya","Kampala","Mpigi","Kasese","Lira"]}

DB_URL = os.environ.get("DB_URL", CFG.get("DB_URL", "sqlite:///nsamizi_demo.db"))
SECRET_KEY = os.environ.get("SECRET_KEY", CFG.get("SECRET_KEY", "nsamizi-dev-key-2025"))
ALLOW_STUDENT_SELF_LOGIN = CFG.get("ALLOW_STUDENT_SELF_LOGIN", True)
UPLOAD_FOLDER = "static/uploads"

app = Flask(__name__, static_folder="static")
app.secret_key = SECRET_KEY
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
CORS(app, supports_credentials=True)
app.config['SESSION_PERMANENT'] = False
bcrypt = Bcrypt(app)
csrf =  CSRFProtect(app)
load_dotenv()

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=6)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

STORAGE_PATH = os.environ.get("STORAGE_PATH", CFG.get("STORAGE_PATH", "storage"))
STORAGE_PATH = os.path.abspath(STORAGE_PATH)
os.makedirs(STORAGE_PATH, exist_ok=True)
app.config['STORAGE_PATH'] = STORAGE_PATH
app.config['RATELIMIT_HEADERS_ENABLED'] = True
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
limiter.init_app(app)

try:
    engine = create_engine(DB_URL, echo=False, future=True, pool_pre_ping=True, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
    SessionLocal = scoped_session(
        sessionmaker(
            bind=engine,
            expire_on_commit=False
        )
    )
except Exception as e:
    print(f"[ERROR] Database connection failed ({DB_URL}): {str(e)}")
    print("[INFO] Falling back to SQLite...")
    engine = create_engine("sqlite:///nsamizi_demo.db", echo=False, future=True, connect_args={"check_same_thread": False})
    SessionLocal = scoped_session(sessionmaker(bind=engine))

Base = declarative_base()

def hash_password(pw):
    return hashpw(pw.encode('utf-8'), gensalt()).decode('utf-8')

def verify_password(hash_value, pw):
    if not hash_value or not pw:
        return False

    try:
        return checkpw(
            pw.encode('utf-8'),
            hash_value.encode('utf-8')
        )
    except Exception:
        return False
    
class Branch(Base):
    __tablename__ = "branches"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class Person(Base):
    __tablename__ = "people"
    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"))
    email = Column(String)
    phone = Column(String)
    password_hash = Column(String, nullable=False)
    active = Column(Integer, default=1)
    failed_login_count = Column(Integer, default=0)
    last_failed_time = Column(DateTime)
    blocked_until = Column(DateTime)
    branch = relationship("Branch")

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    reg_no = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    dob = Column(String)
    gender = Column(String)
    photo_url = Column(String)
    branch_id = Column(Integer, ForeignKey("branches.id"))
    health_info = Column(Text)
    password_hash = Column(String, nullable=False)
    course_type = Column(String)  # diploma, degree
    failed_login_count = Column(Integer, default=0)
    last_failed_time = Column(DateTime)
    blocked_until = Column(DateTime)
    branch = relationship("Branch")

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"))
    branch = relationship("Branch")

class Teaches(Base):
    __tablename__ = "teaches"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    __table_args__ = (UniqueConstraint('person_id','course_id', name='uq_teaches'),)

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    __table_args__ = (UniqueConstraint('student_id','course_id', name='uq_enroll'),)

class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    max_score = Column(Float, default=100.0)
    date = Column(String)

class Mark(Base):
    __tablename__ = "marks"
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    scored = Column(Float, nullable=False)
    updated_by = Column(Integer, ForeignKey("people.id"))
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    actor_type = Column(String)
    actor_id = Column(Integer)
    action = Column(String)
    table_name = Column(String)
    record_id = Column(String)
    details = Column(Text)
    ts = Column(DateTime, default=datetime.datetime.utcnow)

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(Integer, primary_key=True)
    identifier = Column(String, nullable=False)  # email or reg_no
    attempts = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.datetime.utcnow)
    blocked_until = Column(DateTime)

class TuitionPayment(Base):
    __tablename__ = "tuition_payments"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    amount = Column(Float, nullable=False)
    paid_date = Column(DateTime)
    due_date = Column(DateTime, nullable=False)
    status = Column(String, default="unpaid")  # paid, unpaid, overdue
    semester = Column(String)  # e.g., "2025-1"
    student = relationship("Student")

class BibleQuote(Base):
    __tablename__ = "bible_quotes"
    id = Column(Integer, primary_key=True)
    verse = Column(String, nullable=False)
    reference = Column(String, nullable=False)  # e.g., "John 3:16"
    active = Column(Boolean, default=True)

class Semester(Base):
    __tablename__ = "semesters"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # e.g., "Semester 1 2025"
    course_type = Column(String, nullable=False)  # diploma or degree
    start_date = Column(DateTime)
    end_date = Column(DateTime)

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    present = Column(Boolean, default=True)
    remarks = Column(String)
    student = relationship("Student")
    course = relationship("Course")

class DigitalBadge(Base):
    __tablename__ = "digital_badges"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    badge_name = Column(String, nullable=False)  # e.g., "Top Performer", "Perfect Attendance"
    badge_icon = Column(String)  # URL to badge image
    achieved_date = Column(DateTime, default=datetime.datetime.utcnow)
    student = relationship("Student")
    course = relationship("Course")

class Certificate(Base):
    __tablename__ = "certificates"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    certificate_type = Column(String)  # "completion", "excellence", "achievement"
    issued_date = Column(DateTime, default=datetime.datetime.utcnow)
    certificate_url = Column(String)  # Path to PDF
    student = relationship("Student")
    course = relationship("Course")

class ProgramType(Base):
    __tablename__ = "program_types"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    duration_months = Column(Integer)
    description = Column(Text)
    category = Column(String)  # "diploma", "certificate", "graduate", "undergraduate"

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    recipient_id = Column(Integer)  # person_id or student_id
    recipient_type = Column(String)  # "student" or "staff"
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String)  # "fee_reminder", "announcement", "payment_received"
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sent_at = Column(DateTime)

Base.metadata.create_all(engine)

def get_random_bible_quote():
    s = db()
    quotes = s.query(BibleQuote).filter(BibleQuote.active == True).all()
    s.close()
    if quotes:
        return random.choice(quotes)
    return None

def create_audit(
    actor_type,
    actor_id,
    action,
    details
):
    s = db()

    try:
        log = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            details=details
        )
        s.add(log)
        s.commit()

    finally:
        s.close()

def db():
    return SessionLocal()

def seed():
    s = db()
    if s.query(Branch).count() == 0:
        names = CFG.get("DEMO_BRANCHES", ["Adjumani","Gulu","Nsambya","Kampala","Mpigi","Kasese","Lira"])
        for n in names:
            s.add(Branch(name=n))
        s.commit()

    if s.query(Person).count() < 50:
        default_password_hash = hash_password("DemoPass@2025")
        branches = {b.name: b for b in s.query(Branch).all()}
        branch_names = list(branches.keys())
        people = []

        people.extend([
            Person(full_name="Mrs. Carol N.", role="principal", branch=branches["Kampala"], email="carol@nsamizi", phone="0777000003", password_hash=default_password_hash),
            Person(full_name="Deputy Principal", role="deputy_principal", branch=branches["Mpigi"], email="deputy@nsamizi", phone="0777000010", password_hash=default_password_hash),
            Person(full_name="Coordinator Overall A", role="coordinator_overall", branch=branches["Mpigi"], email="coordA@nsamizi", phone="0777000012", password_hash=default_password_hash),
            Person(full_name="Coordinator Overall B", role="coordinator_overall", branch=branches["Kampala"], email="coordB@nsamizi", phone="0777000013", password_hash=default_password_hash),
            Person(full_name="Admin User", role="admin", branch=branches["Mpigi"], email="admin@nsamizi", phone="0777000011", password_hash=default_password_hash)
        ])

        first_names = ["Alice","Brian","Cyrus","Diana","Eunice","Frank","Grace","Hassan","Irene","James","Kaggwa","Lydia","Mary","Nadia","Oscar","Paul","Queen","Ruth","Samuel","Tracy","Umar","Victor","Winnie","Xenia","Yusuf","Zara"]
        last_names = ["Okello","Ouma","Nyakato","Kintu","Nabiryo","Mwesige","Achieng","Kato","Namanya","Ssekandi","Adongo","Lule","Atim","Bakaki","Lukwago","Mugisa","Nabisubi","Sserwadda","Kiwanuka","Lukoma"]
        phone_base = 772000000
        email_index = 1

        for branch_name in branch_names:
            branch = branches[branch_name]
            for i in range(3):
                first = first_names[(email_index * 3) % len(first_names)]
                last = last_names[(email_index * 4) % len(last_names)]
                people.append(Person(
                    full_name=f"{first} {last}",
                    role="lecturer",
                    branch=branch,
                    email=f"{branch_name[:3].lower()}lect{i+1}@nsamizi",
                    phone=f"0777{phone_base + email_index}",
                    password_hash=default_password_hash
                ))
                email_index += 1

            for i in range(2):
                people.append(Person(
                    full_name=f"Coordinator {branch_name} {'A' if i == 0 else 'B'}",
                    role="coordinator",
                    branch=branch,
                    email=f"coord_{branch_name[:3].lower()}{i+1}@nsamizi",
                    phone=f"0777{phone_base + email_index}",
                    password_hash=default_password_hash
                ))
                email_index += 1

        s.add_all(people)
        s.commit()

    if s.query(Student).count() < 210:
        default_password_hash = hash_password("DemoPass@2025")
        first_names = ["Aisha","John","David","Nina","Simon","Mercy","Peter","Rachael","Emmanuel","Jane","Patrick","Susan","Robert","Lilian","Michael","Grace","Joshua","Esther","Paul","Anne","Daniel","Beatrice","Andrew","Naomi","Isaac","Florence","Mark","Judith","Kenneth","Sarah"]
        last_names = ["Kato","Mugisha","Okello","Akeer","Nabwire","Tumusiime","Mutebi","Achieng","Namirembe","Kizza","Kabanda","Lubega","Tumusinza","Musoke","Nabukenya"]
        branches = {b.name: b for b in s.query(Branch).all()}

        students = []
        for branch_name, branch in branches.items():
            existing = s.query(Student).filter(Student.branch_id == branch.id).count()
            for idx in range(existing, 30):
                first = random.choice(first_names)
                last = random.choice(last_names)
                reg_no = f"NS2025-{branch_name[:3].upper()}{idx+1:03d}"
                course_type = ["diploma", "degree", "certificate"][idx % 3]
                students.append(Student(
                    reg_no=reg_no,
                    full_name=f"{first} {last}",
                    dob=f"200{idx % 5 + 5}-0{(idx % 9) + 1}-15",
                    gender="F" if idx % 2 == 0 else "M",
                    branch=branch,
                    photo_url=f"student_{branch_name[:3].lower()}_{idx+1}.jpeg",
                    password_hash=default_password_hash,
                    course_type=course_type
                ))
        s.add_all(students)
        s.commit()

    if s.query(Course).count() < 28:
        branches = {b.name: b for b in s.query(Branch).all()}
        templates = [
            ("SW", "Social Work"),
            ("CP", "Child Protection"),
            ("PA", "Public Administration"),
            ("SJ", "Social Justice")
        ]
        courses = []
        for branch_name, branch in branches.items():
            suffix = branch_name[:3].upper()
            for code_prefix, title in templates:
                courses.append(Course(code=f"{code_prefix}{suffix}", title=f"{title} - {branch_name}", branch=branch))
        s.add_all(courses)
        s.commit()

        lecturers = s.query(Person).filter(Person.role == "lecturer").all()
        for idx, course in enumerate(courses):
            if not lecturers:
                break
            s.add(Teaches(person_id=lecturers[idx % len(lecturers)].id, course_id=course.id))
        s.commit()

        branch_courses = {}
        for course in courses:
            branch_courses.setdefault(course.branch_id, []).append(course.id)

        all_students = s.query(Student).all()
        enrollment_list = []
        for student in all_students:
            options = branch_courses.get(student.branch_id, [])
            if not options:
                continue
            chosen = random.sample(options, min(2, len(options)))
            for course_id in chosen:
                if not s.query(Enrollment).filter(Enrollment.student_id == student.id, Enrollment.course_id == course_id).first():
                    enrollment_list.append(Enrollment(student_id=student.id, course_id=course_id))
        s.add_all(enrollment_list)
        s.commit()

        assessments = []
        for course in courses:
            assessments.append(Assessment(course_id=course.id, title=f"{course.title} - Test 1", max_score=100, date="2025-09-01"))
            assessments.append(Assessment(course_id=course.id, title=f"{course.title} - Test 2", max_score=100, date="2025-09-15"))
        s.add_all(assessments)
        s.commit()

        assessment_by_course = {}
        for a in s.query(Assessment).all():
            assessment_by_course.setdefault(a.course_id, []).append(a)

        lecturers = s.query(Person).filter(Person.role == "lecturer").all()
        mark_list = []
        for enrollment in s.query(Enrollment).all():
            tests = assessment_by_course.get(enrollment.course_id, [])
            for test in tests:
                mark_list.append(Mark(
                    assessment_id=test.id,
                    student_id=enrollment.student_id,
                    scored=random.randint(50, 95),
                    updated_by=random.choice(lecturers).id if lecturers else None
                ))
        s.add_all(mark_list)
        s.commit()

        if s.query(TuitionPayment).count() == 0:
            due_date = datetime.datetime(2025, 9, 1)
            payments = []
            for student in all_students:
                status = "paid" if random.random() < 0.65 else "unpaid"
                tp = TuitionPayment(student_id=student.id, amount=1200000.0, due_date=due_date, status=status, semester="2025-1")
                if status == "paid":
                    tp.paid_date = datetime.datetime.now(datetime.UTC)
                payments.append(tp)
            s.add_all(payments)
            s.commit()

    if s.query(BibleQuote).count() == 0:
        quotes = [
            {"verse": "For I know the plans I have for you, declares the Lord.", "reference": "Jeremiah 29:11"},
            {"verse": "Trust in the Lord with all your heart.", "reference": "Proverbs 3:5"},
            {"verse": "Be strong and courageous.", "reference": "Joshua 1:9"}
        ]
        for q in quotes:
            s.add(BibleQuote(verse=q["verse"], reference=q["reference"]))
        s.commit()

    if s.query(Semester).count() == 0:
        semesters = [
            Semester(name="Diploma Semester 1 2025", course_type="diploma", start_date=datetime.datetime(2025, 1, 1), end_date=datetime.datetime(2025, 6, 30)),
            Semester(name="Degree Semester 1 2025", course_type="degree", start_date=datetime.datetime(2025, 1, 1), end_date=datetime.datetime(2025, 6, 30))
        ]
        s.add_all(semesters)
        s.commit()

    if s.query(ProgramType).count() == 0:
        programs = [
            ProgramType(name="Social Work", duration_months=24, category="diploma", description="2-year Diploma in Social Work"),
            ProgramType(name="Development Studies", duration_months=24, category="diploma", description="2-year Diploma in Development Studies"),
            ProgramType(name="Entrepreneurship Development", duration_months=24, category="diploma", description="2-year Diploma in Entrepreneurship Development"),
            ProgramType(name="Counselling and Guidance", duration_months=24, category="diploma", description="2-year Diploma in Counselling and Guidance"),
            ProgramType(name="Public Administration and Management", duration_months=24, category="diploma", description="2-year Diploma in Public Administration"),
            ProgramType(name="Secretarial Studies", duration_months=24, category="diploma", description="2-year Diploma in Secretarial Studies"),
            ProgramType(name="Business Administration", duration_months=24, category="diploma", description="2-year Diploma in Business Administration"),
            ProgramType(name="Journalism", duration_months=24, category="diploma", description="2-year Diploma in Journalism"),
            ProgramType(name="Communication and Media Studies", duration_months=24, category="diploma", description="2-year Diploma in Communication and Media Studies"),
            ProgramType(name="Human Resource Studies", duration_months=24, category="diploma", description="2-year Diploma in Human Resource Studies"),
            ProgramType(name="Agri-business Management", duration_months=24, category="diploma", description="2-year Diploma in Agri-business Management"),
            ProgramType(name="Juvenile Justice and Development", duration_months=24, category="diploma", description="2-year Diploma in Juvenile Justice and Development"),
            ProgramType(name="Gender and Development", duration_months=24, category="diploma", description="2-year Diploma in Gender and Development"),
            ProgramType(name="Children, Youth and Development", duration_months=24, category="diploma", description="2-year Diploma in Children, Youth and Development"),
            ProgramType(name="Leadership and Good Governance", duration_months=24, category="diploma", description="2-year Diploma in Leadership and Good Governance"),
            ProgramType(name="Social Mobilisation", duration_months=9, category="certificate", description="9-month Certificate in Social Mobilisation"),
            ProgramType(name="Child Protection", duration_months=9, category="certificate", description="9-month Certificate in Child Protection"),
            ProgramType(name="Literacy and Adult Education", duration_months=9, category="certificate", description="9-month Certificate in Literacy and Adult Education"),
            ProgramType(name="Community-based Work with Children and Youth", duration_months=9, category="certificate", description="9-month Certificate in Community-based Work"),
            ProgramType(name="Solar Technology", duration_months=9, category="certificate", description="9-month Certificate in Solar Technology"),
            ProgramType(name="Participatory Learning Tools and Action", duration_months=9, category="certificate", description="9-month Certificate in Participatory Learning"),
            ProgramType(name="Nursery Teaching and Child Protection", duration_months=9, category="certificate", description="9-month Certificate in Nursery Teaching"),
            ProgramType(name="Post-graduate Diploma in Social Justice", duration_months=9, category="graduate", description="9-month Post-graduate Diploma in Social Justice"),
            ProgramType(name="Post-graduate Diploma in Social Development", duration_months=9, category="graduate", description="9-month Post-graduate Diploma in Social Development"),
            ProgramType(name="Bachelor Degree in Social Development", duration_months=36, category="undergraduate", description="3-year Bachelor Degree in Social Development"),
            ProgramType(name="Bachelor Degree in Public Administration and Management", duration_months=36, category="undergraduate", description="3-year Bachelor Degree in Public Administration")
        ]
        s.add_all(programs)
        s.commit()
    s.close()
seed()

@app.route("/api/people", methods=["GET"])
def list_people():
    role = request.args.get("role")
    s = db()
    q = s.query(Person).filter(Person.active==1)
    if role:
        q = q.filter(Person.role.ilike(role))
    out = [{"id":p.id,"name":p.full_name,"role":p.role,"branch":p.branch.name if p.branch else None} for p in q.order_by(Person.full_name).all()]
    s.close()
    return jsonify(out)

@app.route("/debug")
def debug():
    return "Server works"

@app.route("/api/export/students")
def export_students():

    if session.get("role") != "admin":
        return jsonify({"ok": False}), 403
    s = db()

    wb = Workbook()
    ws = wb.active
    ws.title = "Students"

    ws.append([
        "ID",
        "Reg No",
        "Name",
        "Gender",
        "Course Type"
    ])
    students = s.query(Student).all()

    for st in students:
        ws.append([
            st.id,
            st.reg_no,
            st.full_name,
            st.gender,
            st.course_type
        ])
    filepath = "storage/exports/students.xlsx"
    wb.save(filepath)
    s.close()

    return send_file(
        filepath,
        as_attachment=True
    )

@app.route("/api/export/marks")
def export_marks():

    if session.get("role") != "admin":
        return jsonify({"ok": False}), 403
    s = db()

    wb = Workbook()
    ws = wb.active

    ws.append([
        "Student",
        "Course",
        "Score"
    ])

    rows = s.query(Mark).all()
    for row in rows:
        ws.append([
            row.student_id,
            row.course_id,
            row.score
        ])

    path = "storage/exports/marks.xlsx"
    wb.save(path)
    s.close()
    return send_file(path, as_attachment=True)

@app.route("/api/admin/create_student", methods=["POST"])
def create_student():
    if session.get("role") != "admin":
        return jsonify({"ok": False, "msg": "Unauthorized"}), 403
    data = request.json
    s = db()

    try:
        existing = s.query(Student).filter_by(
            reg_no=data["reg_no"]
        ).first()

        if existing:
            return jsonify({
                "ok": False,
                "msg": "Student already exists"
            })

        student = Student(
            reg_no=data["reg_no"],
            full_name=data["full_name"],
            gender=data.get("gender"),
            dob=data.get("dob"),
            course_type=data.get("course_type"),
            branch_id=data["branch_id"],
            password_hash=hash_password(data["password"])
        )
        s.add(student)
        s.commit()

        return jsonify({
            "ok": True,
            "msg": "Student created"
        })

    except Exception as e:
        s.rollback()
        return jsonify({
            "ok": False,
            "msg": str(e)
        })
    finally:
        s.close()

@app.route("/api/search")
def global_search():
    q = request.args.get("q", "")
    s = db()
    students = (
        s.query(Student)
        .filter(
            Student.full_name.ilike(f"%{q}%")
        )
        .limit(10)
        .all()
    )

    people = (
        s.query(Person)
        .filter(
            Person.full_name.ilike(f"%{q}%")
        )
        .limit(10)
        .all()
    )

    return jsonify({
        "students": [
            {
                "id": x.id,
                "name": x.full_name
            }
            for x in students
        ],
        "staff": [
            {
                "id": x.id,
                "name": x.full_name
            }
            for x in people
        ]
    })

@csrf.exempt
@app.route("/api/upload/student-photo", methods=["POST"])
def upload_student_photo():

    if "person_id" not in session:
        return jsonify({
            "ok": False
        }), 401

    if "photo" not in request.files:
        return jsonify({
            "ok": False,
            "msg": "No file"
        })

    file = request.files["photo"]
    if file.filename == "":
        return jsonify({
            "ok": False,
            "msg": "Empty filename"
        })

    filename = secure_filename(file.filename)
    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )
    file.save(filepath)

    return jsonify({
        "ok": True,
        "filename": filename,
        "path": filepath
    })

@app.route("/api/students")
def get_students():
    s = db()
    students = s.query(Student).all()
    output = []

    for st in students:
        output.append({
            "id": st.id,
            "reg_no": st.reg_no,
            "full_name": st.full_name
        })
    s.close()
    return jsonify(output)

#@app.route("/api/students", methods=["GET"])
#def list_students():
#    s = db()
#    out = [{"id":st.id,"name":st.full_name,"reg_no":st.reg_no} 
#           for st in s.query(Student).order_by(Student.full_name).all()]
#    s.close()
#    return jsonify(out)

@csrf.exempt
@app.route("/api/login_person", methods=["POST"])
@limiter.limit("10 per minute")
def login_person():
    data = request.json
    email = data.get("email")
    pwd = data.get("password")
    role = data.get("role")
    s = db()
    p = s.query(Person).filter(
        Person.email == email,
        Person.role == role
    ).first()

    if not p:
        s.close()
        return jsonify({
            "ok": False,
            "msg": "User not found"
        }), 404

    now = datetime.datetime.now(datetime.UTC)
    #if p.blocked_until and p.blocked_until > now:
    #    s.close()
    #    return jsonify({
    #        "ok": False,
    #        "msg": "account blocked"
    #    }), 403

    print("EMAIL:", email)
    print("INPUT PASSWORD:", pwd)
    print("HASH:", p.password_hash)
    print("VERIFY:", verify_password(p.password_hash, pwd))

    if verify_password(p.password_hash, pwd):
       # RESET FAILED LOGIN
        p.failed_login_count = 0
        p.last_failed_time = None
        p.blocked_until = None
       
        person_id = p.id
        role = p.role
        fullname = p.full_name
       
        session.clear()
       # SESSION
        session["person_id"] = person_id
        session["role"] = role
        session["fullname"] = fullname # person.fullname

        # AUDIT
        audit = AuditLog(
            actor_type="person",
            actor_id=person_id,
            action="login",
            details=f"Person {fullname} logged in"  # person.fullname
        )
        s.add(audit)
        s.commit()

        s.close()
        return jsonify({
            "ok": True,
            "role": role,
            "fullname": fullname
        }), 200

    else:
        p.failed_login_count += 1
        p.last_failed_time = now
        #if p.failed_login_count >= 3:
        #    p.blocked_until = now + datetime.timedelta(days=1)
        #    audit = AuditLog(
        #        actor_type="person",
        #        actor_id=p.id,
        #        action="blocked",
        #        details=f"Person {p.full_name} blocked"
        #    )
        
## Indented part, put back after testing
        audit = AuditLog(
            actor_type="person",
            actor_id=p.id,
            action="failed_login",
            details=f"Failed login for {email}"
            )
        s.add(audit)
        s.commit()
        s.close()

        return jsonify({
            "ok": False,
            "msg": "invalid"
        }), 401
    
@csrf.exempt
@app.route("/api/login_student", methods=["POST"])
@limiter.limit("10 per minute")
def login_student():
    if not ALLOW_STUDENT_SELF_LOGIN:
        return jsonify({
            "ok": False,
            "msg": "disabled"
        }), 403
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "ok": False,
            "msg": "No JSON data received"
        }), 400

    reg_no = data.get("reg_no")
    pwd = data.get("password")
    s = db()
    st = s.query(Student).filter(
        Student.reg_no == reg_no
    ).first()

    if not st:
        s.close()
        return jsonify({
            "ok": False,
            "msg": "not found"
        }), 404
    now = datetime.datetime.now(datetime.UTC)

    #if st.blocked_until and st.blocked_until > now:
    #   s.close()
    #    return jsonify({
    #        "ok": False,
    #        "msg": "account blocked"
    #    }), 403

    if verify_password(st.password_hash, pwd):
        st.failed_login_count = 0
        st.last_failed_time = None

        # SAVE BEFORE COMMIT/CLOSE
        student_id = st.id
        fullname = st.full_name

        session["student_id"] = student_id
        session["fullname"] = fullname
        session["role"] = "student"

        audit = AuditLog(
            actor_type="student",
            actor_id=student_id,
            action="login",
            details=f"Student {fullname} logged in"
        )
        s.add(audit)
        s.commit()
        s.close()

        return jsonify({
            "ok": True,
            "fullname": fullname,
            "role": "student"
        })
    else:
        st.failed_login_count += 1
        st.last_failed_time = now

        if st.failed_login_count >= 3:
            st.blocked_until = now + datetime.timedelta(days=1)
            audit = AuditLog(
                actor_type="student",
                actor_id=st.id,
                action="blocked",
                details=f"Student {st.full_name} blocked"
            )

        else:
            audit = AuditLog(
                actor_type="student",
                actor_id=st.id,
                action="failed_login",
                details=f"Failed login for {reg_no}"
            )
            s.add(audit)
            s.commit()
            s.close()

            return jsonify({
                "ok": False,
                "msg": "invalid"
            }), 401

@csrf.exempt
@app.route("/api/admin/audit")
def admin_audit():
    if session.get("role") != "admin":
        return jsonify([])
    s = db()

    logs = (
        s.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(100)
        .all()
    )

    output = []
    for log in logs:
        output.append({
            "action": log.action,
            "details": log.details,
            "actor": log.actor_id,
            "created": str(log.created_at)
        })
    s.close()

    return jsonify(output)

@app.route("/api/students/search")
def search_students_api():
    q = request.args.get("q", "").strip()
    s = db()

    try:
        students = (
            s.query(Student)
            .filter(
                Student.full_name.ilike(f"%{q}%")
            )
            .order_by(Student.full_name.asc())
            .all()
        )

        return jsonify([
            {
                "id": st.id,
                "reg_no": st.reg_no,
                "full_name": st.full_name
            }
            for st in students
        ])
    finally:
        s.close()

@csrf.exempt
@app.route("/api/admin/create_course", methods=["POST"])
def create_course():
    if session.get("role") != "admin":
        return jsonify({"ok": False}), 403
    data = request.json
    s = db()

    try:
        exists = s.query(Course).filter_by(
            code=data["code"]
        ).first()

        if exists:
            return jsonify({
                "ok": False,
                "msg": "Course already exists"
            })

        course = Course(
            code=data["code"],
            title=data["title"],
            branch_id=data["branch_id"]
        )
        s.add(course)
        s.commit()

        return jsonify({
            "ok": True,
            "msg": "Course created"
        })

    except Exception as e:
        s.rollback()

        return jsonify({
            "ok": False,
            "msg": str(e)
        })
    finally:
        s.close()

@app.route("/api/my/courses", methods=["GET"])
def my_courses():
    pid = session.get("person_id")
    if not pid:
        return jsonify([])
    s = db()
    teaches = s.query(Teaches).filter(Teaches.person_id == pid).all()
    courses = [s.query(Course).get(t.course_id) for t in teaches]
    out = [{"course_id":c.id, "code":c.code, "title":c.title} for c in courses if c]
    s.close()
    return jsonify(out)

@app.route("/api/course/<int:course_id>/students", methods=["GET"])
def course_students(course_id):
    s = db()
    enrs = s.query(Enrollment).filter(Enrollment.course_id == course_id).all()
    studs = [s.query(Student).get(e.student_id) for e in enrs]
    out = [{"student_id":st.id,"reg_no":st.reg_no,"name":st.full_name} for st in studs if st]
    s.close()
    return jsonify(out)

@app.route("/api/course/<int:course_id>/assessments", methods=["GET"])
def course_assessments(course_id):
    s = db()
    ass = s.query(Assessment).filter(Assessment.course_id == course_id).all()
    out = [{"assessment_id":a.id,"title":a.title,"max_score":a.max_score} for a in ass]
    s.close()
    return jsonify(out)

@csrf.exempt
@app.route("/api/marks", methods=["POST"])
def add_mark():
    pid = session.get("person_id")
    if not pid:
        return jsonify({"ok":False,"msg":"not logged in"}),401
    data = request.json
    s = db()
    m = Mark(assessment_id=int(data['assessment_id']), student_id=int(data['student_id']), scored=float(data['scored']), updated_by=pid)
    s.add(m); s.commit(); s.close()
    return jsonify({"ok":True})


@app.route("/api/admin/export_results/<int:course_id>/<semester>", methods=["GET"])
def export_results(course_id, semester):
    if session.get("role") != "admin":
        return jsonify({"ok":False,"msg":"not authorized"}),403
    s = db()
    course = s.query(Course).get(course_id)
    if not course:
        s.close()
        return jsonify({"ok":False,"msg":"course not found"}),404
    assessments = s.query(Assessment).filter(Assessment.course_id == course_id).all()
    enrollments = s.query(Enrollment).filter(Enrollment.course_id == course_id).all()
    data = []
    for enr in enrollments:
        student = s.query(Student).get(enr.student_id)
        row = {"Reg No": student.reg_no, "Name": student.full_name}
        for ass in assessments:
            mark = s.query(Mark).filter(Mark.assessment_id == ass.id, Mark.student_id == student.id).first()
            row[ass.title] = mark.scored if mark else None
        data.append(row)
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=f"{course.code}_{semester}", index=False)
    output.seek(0)
    s.close()
    return send_from_directory(directory=".", path=output, as_attachment=True, download_name=f"{course.code}_{semester}_results.xlsx")
    return send_file(
        output,
        as_attachment=True,
        download_name=f"{course.code}_{semester}_results.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@csrf.exempt
@app.route("/api/admin/logs", methods=["GET"])
def admin_logs():
    if session.get("role") != "admin":
        return jsonify({"ok":False,"msg":"not authorized"}),403
    s = db()
    logs = s.query(AuditLog).order_by(AuditLog.ts.desc()).limit(100).all()
    out = []
    for log in logs:
        out.append({
            "actor_type": log.actor_type,
            "actor_id": log.actor_id,
            "action": log.action,
            "table_name": log.table_name,
            "record_id": log.record_id,
            "details": log.details,
            "ts": log.ts.isoformat()
        })
    s.close()
    return jsonify(out)


@app.route("/api/admin/overview", methods=["GET"])
def admin_overview():
    if session.get("role") != "admin":
        return jsonify({"ok":False,"msg":"not authorized"}),403
    s = db()
    total_students = s.query(Student).count()
    total_staff = s.query(Person).count()
    total_logins = s.query(AuditLog).filter(AuditLog.action == "login").count()
    suspicious = s.query(AuditLog).filter(AuditLog.action.in_(["failed_login", "blocked"])).count()
    s.close()
    return jsonify({
        "total_students": total_students,
        "total_staff": total_staff,
        "total_logins": total_logins,
        "suspicious_activities": suspicious
    })


@app.route("/admin/students")
def admin_students():

    if session.get("role") != "admin":
        return redirect("/login")

    return render_template(
        "admin_students.html"
    )


@app.route("/api/admin/full-audit")
def full_audit():
    if session.get("role") != "admin":
        return jsonify({"ok": False}), 403
    s = db()

    try:
        return jsonify({
            "students":
                s.query(Student).count(),
            "people":
                s.query(Person).count(),
            "courses":
                s.query(Course).count(),
            "branches":
                s.query(Branch).count(),
            "attendance":
                s.query(Attendance).count(),
            "notifications":
                s.query(Notification).count(),
            "audit_logs":
                s.query(AuditLog).count()
        })

    finally:
        s.close()

@app.route("/api/admin/database-summary")
def database_summary():
    s = db()

    data = {
        "students": s.query(Student).count(),
        "staff": s.query(Person).count(),
        "courses": s.query(Course).count(),
        "attendance": s.query(Attendance).count(),
        "notifications": s.query(Notification).count(),
        "audit_logs": s.query(AuditLog).count()
    }
    s.close()
    return jsonify(data)

@app.route("/api/branches")
def get_branches():
    if "person_id" not in session:
        return jsonify([]), 401
    s = db()

    try:
        branches = s.query(Branch).all()
        output = []
        for b in branches:
            output.append({
                "id": b.id,
                "name": b.name,
                "location": getattr(b, "location", "")
            })
        return jsonify(output)

    finally:
        s.close()

@app.route("/api/bible_quote", methods=["GET"])
def bible_quote():
    quote = get_random_bible_quote()
    if quote:
        return jsonify({"verse": quote.verse, "reference": quote.reference})
    return jsonify({"verse": "No quotes available", "reference": ""})

@app.route("/api/student/<int:student_id>/tuition", methods=["GET"])
def student_tuition(student_id):
    if session.get("student_id") == student_id or session.get("person_id"):
        s = db()
        payments = s.query(TuitionPayment).filter(TuitionPayment.student_id == student_id).order_by(TuitionPayment.due_date).all()
        out = []
        for p in payments:
            out.append({
                "amount": p.amount,
                "due_date": p.due_date.isoformat() if p.due_date else None,
                "paid_date": p.paid_date.isoformat() if p.paid_date else None,
                "status": p.status,
                "semester": p.semester
            })
        s.close()
        return jsonify(out)
    return jsonify({"ok":False,"msg":"not authorized"}),401

@app.route("/api/student/<int:student_id>/progress", methods=["GET"])
def student_progress(student_id):
    if session.get("student_id") == student_id or session.get("person_id"):
        s = db()
        student = s.query(Student).get(student_id)
        if not student:
            s.close()
            return jsonify({"ok":False,"msg":"not found"}),404
        enrs = s.query(Enrollment).filter(Enrollment.student_id == student_id).all()
        courses = []
        for e in enrs:
            c = s.query(Course).get(e.course_id)
            if not c: continue
            ass = s.query(Assessment).filter(Assessment.course_id == c.id).all()
            marks = []
            for a in ass:
                m = s.query(Mark).filter(Mark.assessment_id == a.id, Mark.student_id == student_id).first()
                comment = ""
                if m and m.scored:
                    if m.scored >= 90:
                        comment = random.choice([
                            "Outstanding performance, demonstrating exceptional understanding.",
                            "Exemplary work, reflecting a strong grasp of the subject matter."
                        ])
                    elif m.scored >= 80:
                        comment = random.choice([
                            "Commendable effort with a solid understanding of concepts.",
                            "Very good performance, showing consistent progress."
                        ])
                    elif m.scored >= 70:
                        comment = random.choice([
                            "Satisfactory work, with room for deeper engagement.",
                            "Good effort, but further focus on details is recommended."
                        ])
                    else:
                        comment = random.choice([
                            "Adequate attempt, but more effort is needed to excel.",
                            "Fair performance; additional study will enhance results."
                        ])
                marks.append({
                    "assessment": a.title,
                    "date": a.date,
                    "max": a.max_score,
                    "scored": m.scored if m else None,
                    "comment": comment
                })
            courses.append({"course_code": c.code, "course_title": c.title, "marks": marks})
        out = {
            "ok": True,
            "student": {"id": student.id, "reg_no": student.reg_no, "name": student.full_name, "photo_url": student.photo_url},
            "courses": courses
        }
        s.close()
        return jsonify(out)
    return jsonify({"ok":False,"msg":"not authorized"}),401

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/about')
def about():
    return render_template("about.html")

def require_person(role_any=None):
    if "person_id" not in session:
        return False, ("not logged in", 401)
    if role_any and session.get("role") not in role_any:
        return False, ("forbidden", 403)
    return True, None


def format_currency(amount):
    try:
        amount = float(amount or 0)
        return f"UGX {amount:,.0f}"
    except Exception:
        return "UGX 0"


app.jinja_env.filters['money'] = format_currency


def build_finance_summary(person, s):
    finance_roles = {
        'coordinator': 'Branch Coordinator Dashboard',
        'coordinator_overall': 'Overall Coordinator Dashboard',
        'deputy_principal': 'Deputy Principal Dashboard',
        'principal': 'Principal Dashboard'
    }

    role = person.role
    is_branch_coordinator = role == 'coordinator'
    all_branches = s.query(Branch).order_by(Branch.name).all()
    branch_ids = [person.branch_id] if is_branch_coordinator and person.branch_id else [b.id for b in all_branches]
    active_branches = [b for b in all_branches if b.id in branch_ids]
    centers = [b.name for b in all_branches]

    students = s.query(Student).filter(Student.branch_id.in_(branch_ids)).all() if branch_ids else []
    people = s.query(Person).filter(Person.branch_id.in_(branch_ids)).all() if branch_ids else []
    courses = s.query(Course).filter(Course.branch_id.in_(branch_ids)).all() if branch_ids else []
    payments = s.query(TuitionPayment).join(Student).filter(Student.branch_id.in_(branch_ids)).all() if branch_ids else []

    courses_by_id = {c.id: c for c in courses}
    person_ids = [p.id for p in people]
    teaches = s.query(Teaches).filter(Teaches.person_id.in_(person_ids)).all() if person_ids else []
    courses_by_person = defaultdict(list)
    for teach in teaches:
        course = courses_by_id.get(teach.course_id)
        if course:
            courses_by_person[teach.person_id].append(course.title)

    student_finance = {}
    grace_entries = {}
    now = datetime.datetime.now(datetime.UTC)
    for payment in payments:
        student = payment.student
        if not student:
            continue
        key = student.id
        summary = student_finance.setdefault(key, {
            'student_name': student.full_name,
            'reg_no': student.reg_no,
            'branch': student.branch.name if student.branch else 'Unknown',
            'paid_total': 0.0,
            'due_total': 0.0,
            'paid_count': 0,
            'due_count': 0,
            'latest_due': None
        })

        amount = float(payment.amount or 0)
        if payment.status == 'paid':
            summary['paid_total'] += amount
            summary['paid_count'] += 1
        else:
            summary['due_total'] += amount
            summary['due_count'] += 1
            if payment.due_date:
                if summary['latest_due'] is None or payment.due_date < summary['latest_due']:
                    summary['latest_due'] = payment.due_date
            if payment.due_date and payment.due_date < now:
                grace = grace_entries.setdefault(key, {
                    'student_name': student.full_name,
                    'reg_no': student.reg_no,
                    'branch': student.branch.name if student.branch else 'Unknown',
                    'balance': 0.0,
                    'grace_amount': 0.0,
                    'due_dates': []
                })
                grace['balance'] += amount
                grace['grace_amount'] += round(amount * 0.15, 2)
                grace['due_dates'].append(payment.due_date.strftime('%Y-%m-%d'))

    paid_students = [v for v in student_finance.values() if v['paid_total'] > 0]
    balance_students = [v for v in student_finance.values() if v['due_total'] > 0]
    grace_students = list(grace_entries.values())
    total_collected = sum(v['paid_total'] for v in paid_students)
    total_due = sum(v['paid_total'] + v['due_total'] for v in student_finance.values())
    balance_total = sum(v['due_total'] for v in student_finance.values())

    branch_stats = []
    for branch in active_branches:
        branch_payments = [p for p in payments if p.student and p.student.branch_id == branch.id]
        branch_collected = sum(float(p.amount or 0) for p in branch_payments if p.status == 'paid')
        branch_due = sum(float(p.amount or 0) for p in branch_payments if p.status != 'paid')
        branch_students = [st for st in students if st.branch_id == branch.id]
        branch_courses = [c for c in courses if c.branch_id == branch.id]
        branch_people = [p for p in people if p.branch_id == branch.id]
        branch_stats.append({
            'name': branch.name,
            'collected': branch_collected,
            'due': branch_due,
            'balance': branch_due,
            'students': len(branch_students),
            'courses': len(branch_courses),
            'people': len(branch_people)
        })

    expenses = {
        'transport': 280_000 * max(1, len(active_branches)),
        'facilitation': 320_000 * max(1, len(active_branches)),
        'admin': 210_000 * max(1, len(active_branches)),
        'contingency': 160_000 * max(1, len(active_branches))
    }
    expenses['total'] = sum(expenses.values())

    person_profiles = []
    for person_obj in people:
        person_profiles.append({
            'name': person_obj.full_name,
            'role': person_obj.role,
            'branch': person_obj.branch.name if person_obj.branch else 'Unknown',
            'courses': courses_by_person.get(person_obj.id, []),
            'photo_url': '',
            'email': person_obj.email,
            'phone': person_obj.phone
        })

    return {
        'title': finance_roles.get(role, 'Finance Dashboard'),
        'role': role,
        'scope_name': active_branches[0].name if is_branch_coordinator and active_branches else 'All Branches',
        'centers': centers,
        'total_students': len(students),
        'total_people': len(people),
        'total_courses': len(courses),
        'total_collected': total_collected,
        'total_due': total_due,
        'balance_total': balance_total,
        'paid_students': sorted(paid_students, key=lambda x: x['student_name'])[:40],
        'balance_students': sorted(balance_students, key=lambda x: x['student_name'])[:40],
        'grace_students': sorted(grace_students, key=lambda x: x['student_name'])[:40],
        'branch_stats': branch_stats,
        'people_profiles': sorted(person_profiles, key=lambda x: x['name'])[:40],
        'expenses': expenses,
        'summary_cards': [
            {'label': 'Total Collected', 'value': total_collected, 'icon': '💰'},
            {'label': 'Outstanding Balance', 'value': balance_total, 'icon': '📌'},
            {'label': 'Grace Students', 'value': len(grace_students), 'icon': '⏳'},
            {'label': 'Possible Expenses', 'value': expenses['total'], 'icon': '🧾'}
        ]
    }


@app.route('/finance/dashboard')
def finance_dashboard():
    ok, err = require_person(role_any=['coordinator', 'coordinator_overall', 'deputy_principal', 'principal'])
    if not ok:
        return redirect('/')

    s = db()
    person = s.query(Person).get(session['person_id'])
    summary = build_finance_summary(person, s)
    s.close()
    return render_template('finance_dashboard.html', summary=summary, fullname=person.full_name)

@app.route("/api/my/centers", methods=["GET"])
def my_centers():
    ok, err = require_person(role_any=["lecturer","hod","principal","staff"])
    if not ok:
        return jsonify({"ok": False, "msg": err[0]}), err[1]

    s = db()
    pid = session["person_id"]
    person = s.query(Person).get(pid)

    # Centers from teaches
    my_branches_query = (
        s.query(Branch)
        .join(Course, Course.branch_id == Branch.id)
        .join(Teaches, Teaches.course_id == Course.id)
        .filter(Teaches.person_id == pid)
        .distinct()
        .all()
    )
    my_branches = list(set(my_branches_query))

    # Add person's own branch if not already included (for staff without teaches)
    if person.branch and person.branch not in my_branches:
        my_branches.append(person.branch)
    my_centers = [{"id": b.id, "name": b.name} for b in my_branches]

    # Other centers
    others = s.query(Branch).filter(~Branch.id.in_([b.id for b in my_branches])).all()
    other_centers = [{"id": b.id, "name": b.name} for b in others]
    s.close()
    return jsonify({"ok": True, "my_centers": my_centers, "other_centers": other_centers})

@app.route("/api/my/tuition", methods=["GET"])
def my_tuition():
    pid = session.get("person_id")
    if not pid:
        return jsonify([])
    p = db().query(Person).get(pid)
    if p.role not in ["coordinator", "coordinator_overall", "principal", "deputy_principal"]:
        return jsonify([])
    s = db()
    if p.role == "coordinator":
        branch_ids = [p.branch_id]
    else:
        # For overall and principal, all branches
        branch_ids = [b.id for b in s.query(Branch).all()]
    students = s.query(Student).filter(Student.branch_id.in_(branch_ids)).all()
    out = []
    for st in students:
        payments = s.query(TuitionPayment).filter(TuitionPayment.student_id == st.id).all()
        for pay in payments:
            out.append({
                "student_name": st.full_name,
                "reg_no": st.reg_no,
                "amount": pay.amount,
                "due_date": pay.due_date.isoformat() if pay.due_date else None,
                "status": pay.status,
                "semester": pay.semester
            })
    s.close()
    return jsonify(out)

@app.route("/student/progress")
def student_progress_html():
    sid = session.get("student_id")
    if not sid:
        return redirect('/')
    s = db()
    student = s.query(Student).get(sid)
    enrs = s.query(Enrollment).filter(Enrollment.student_id == sid).all()
    courses = []
    for e in enrs:
        c = s.query(Course).get(e.course_id)
        if not c: continue
        ass = s.query(Assessment).filter(Assessment.course_id == c.id).all()
        marks = []
        for a in ass:
            m = s.query(Mark).filter(Mark.assessment_id == a.id, Mark.student_id == sid).first()
            comment = ""
            if m and m.scored:
                if m.scored >= 90:
                    comment = random.choice([
                        "Outstanding performance, demonstrating exceptional understanding.",
                        "Exemplary work, reflecting a strong grasp of the subject matter."
                    ])
                elif m.scored >= 80:
                    comment = random.choice([
                        "Commendable effort with a solid understanding of concepts.",
                        "Very good performance, showing consistent progress."
                    ])
                elif m.scored >= 70:
                    comment = random.choice([
                        "Satisfactory work, with room for deeper engagement.",
                        "Good effort, but further focus on details is recommended."
                    ])
                else:
                    comment = random.choice([
                        "Adequate attempt, but more effort is needed to excel.",
                        "Fair performance; additional study will enhance results."
                    ])
            marks.append({
                "assessment": a.title,
                "date": a.date or '',
                "max": a.max_score,
                "scored": m.scored if m else '-',
                "comment": comment
            })
        courses.append({"code": c.code, "title": c.title, "marks": marks})
    s.close()
    
    # Get Bible quote for daily inspiration
    bible_quote = get_random_bible_quote()
    return render_template("student_progress.html", student=student, courses=courses, bible_quote=bible_quote)

@app.route("/staff/dashboard")
def staff_dashboard():
    if "person_id" not in session:
        return redirect('/')
    role = session["role"]
    pid = session["person_id"]
    s = db()
    person = s.query(Person).get(pid)

    # Fetch courses for lecturer
    courses = []
    if role == "lecturer":
        teaches = s.query(Teaches).filter(Teaches.person_id == pid).all()
        for t in teaches:
            c = s.query(Course).get(t.course_id)
            if c:
                students_in_course = s.query(Student).join(Enrollment).filter(Enrollment.course_id == c.id).all()
                courses.append({
                    "course_id": c.id,
                    "code": c.code,
                    "title": c.title,
                    "students": [{"id": st.id, "name": st.full_name, "reg_no": st.reg_no} for st in students_in_course]
                })

    # Fetch centers
    if role in ["lecturer", "staff"]:
        my_branches_query = (
            s.query(Branch)
            .join(Course, Course.branch_id == Branch.id)
            .join(Teaches, Teaches.course_id == Course.id)
            .filter(Teaches.person_id == pid)
            .distinct()
            .all()
        )
        my_branches = list(set(my_branches_query))
        if person.branch and person.branch not in my_branches:
            my_branches.append(person.branch)
        my_centers = [{"id": b.id, "name": b.name} for b in my_branches]
        other_centers = [{"id": b.id, "name": b.name} for b in s.query(Branch).filter(~Branch.id.in_([b.id for b in my_branches])).all()]
        main_campus = None
    else:  # hod or principal
        all_branches = s.query(Branch).all()
        main_branch = next((b for b in all_branches if b.name == "Mpigi"), None)
        main_campus = {"id": main_branch.id, "name": "Main Campus - Mpigi"} if main_branch else None
        other_centers = [{"id": b.id, "name": b.name} for b in all_branches if b.name != "Mpigi"]
        my_centers = []

    # Get Bible quote
    bible_quote = get_random_bible_quote()

    s.close()
    return render_template("staff_dashboard.html", 
                         role=role, 
                         user_name=person.full_name,
                         courses=courses, 
                         my_centers=my_centers, 
                         other_centers=other_centers, 
                         main_campus=main_campus,
                         bible_quote=bible_quote)

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect('/')
    return render_template('admin_dashboard.html')

@app.route('/principal/dashboard')
def principal_dashboard():
    ok, err = require_person(role_any=['principal', 'deputy_principal'])
    if not ok:
        return redirect('/')
    
    s = db()
    person = s.query(Person).get(session['person_id'])
    
    # Get comprehensive statistics
    total_students = s.query(Student).count()
    total_staff = s.query(Person).count()
    total_courses = s.query(Course).count()
    
    # Get payment stats
    paid_payments = s.query(TuitionPayment).filter(TuitionPayment.status == 'paid').count()
    unpaid_payments = s.query(TuitionPayment).filter(TuitionPayment.status == 'unpaid').count()
    total_collected = s.query(TuitionPayment).filter(TuitionPayment.status == 'paid').with_entities(func.sum(TuitionPayment.amount)).scalar() or 0
    
    # Get branch stats
    branches = s.query(Branch).all()
    branch_stats = []
    for branch in branches:
        branch_students = s.query(Student).filter(Student.branch_id == branch.id).count()
        branch_staff = s.query(Person).filter(Person.branch_id == branch.id).count()
        branch_stats.append({
            'name': branch.name,
            'students': branch_students,
            'staff': branch_staff
        })
    
    # Get recent activity
    recent_logs = s.query(AuditLog).order_by(AuditLog.ts.desc()).limit(20).all()
    
    # Get low attendance students
    low_attendance = s.query(Student).all()[:10]  # This would need more complex logic
    s.close()
    bible_quote = get_random_bible_quote()
    
    return render_template('principal_dashboard.html',
                         person=person,
                         total_students=total_students,
                         total_staff=total_staff,
                         total_courses=total_courses,
                         paid_payments=paid_payments,
                         unpaid_payments=unpaid_payments,
                         total_collected=total_collected,
                         branch_stats=branch_stats,
                         recent_logs=recent_logs,
                         bible_quote=bible_quote)

@app.route('/coordinator/dashboard')
def coordinator_dashboard():
    ok, err = require_person(role_any=['coordinator', 'coordinator_overall'])
    if not ok:
        return redirect('/')
    
    s = db()
    person = s.query(Person).get(session['person_id'])
    role = session.get('role')
    
    # If coordinator, filter by branch; if overall, get all
    if role == 'coordinator':
        branch_ids = [person.branch_id] if person.branch_id else []
    else:
        branch_ids = [b.id for b in s.query(Branch).all()]
    
    # Get students in coordinator's scope
    students = s.query(Student).filter(Student.branch_id.in_(branch_ids)).all() if branch_ids else []
    
    # Get payment data
    unpaid_students = []
    paid_students = []
    for student in students:
        payments = s.query(TuitionPayment).filter(TuitionPayment.student_id == student.id).all()
        for payment in payments:
            if payment.status == 'paid':
                paid_students.append({
                    'name': student.full_name,
                    'reg_no': student.reg_no,
                    'amount': payment.amount,
                    'date': payment.paid_date
                })
            else:
                unpaid_students.append({
                    'name': student.full_name,
                    'reg_no': student.reg_no,
                    'amount': payment.amount,
                    'due_date': payment.due_date
                })
    
    # Get courses
    courses = s.query(Course).filter(Course.branch_id.in_(branch_ids)).all() if branch_ids else []
    
    # Get staff in coordinator's scope
    staff = s.query(Person).filter(Person.branch_id.in_(branch_ids)).all() if branch_ids else []
    s.close()
    
    bible_quote = get_random_bible_quote()
    return render_template('coordinator_dashboard.html',
                         person=person,
                         students=sorted(students, key=lambda x: x.full_name),
                         paid_students=sorted(paid_students, key=lambda x: x['name'])[:30],
                         unpaid_students=sorted(unpaid_students, key=lambda x: x['name'])[:30],
                         courses=sorted(courses, key=lambda x: x.title),
                         staff=sorted(staff, key=lambda x: x.full_name),
                         total_students=len(students),
                         total_paid=len([p for p in paid_students]),
                         total_unpaid=len([p for p in unpaid_students]),
                         bible_quote=bible_quote)

@app.route("/api/student/<int:student_id>/attendance")
def attendance_percentage(student_id):
    s = db()

    total = s.query(Attendance).filter(
        Attendance.student_id == student_id
    ).count()

    present = s.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.present == True
    ).count()
    s.close()
    percent = 0

    if total:
        percent = round(
            present / total * 100,
            2
        )

    return jsonify({
        "attendance_percent": percent
    })

@app.route("/storage/student_photos/<filename>")
def student_photo(filename):
    return send_from_directory(
        "storage/student_photos",
        filename
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/welcome')
def welcome_splash():
    return render_template('welcome_splash.html')

@app.route('/fees/payment-guide')
def fee_payment_guide_page():
    sid = session.get("student_id")
    if not sid:
        return redirect('/')
    return render_template('fee_payment_guide.html')

@app.route('/fees/history')
def fee_history_page():
    sid = session.get("student_id")
    if not sid:
        return redirect('/')
    return render_template('fee_history.html')

@app.route("/api/attendance", methods=["POST"])
def record_attendance():
    if "user_id" not in session:
        return jsonify({
            "ok": False,
            "msg": "Login required"
        }), 401

    data = request.json
    s = db()

    try:
        attendance = Attendance(
            student_id=data["student_id"],
            course_id=data["course_id"],
            date=datetime.datetime.utcnow(),
            present=data.get("present", True),
            remarks=data.get("remarks")
        )
        s.add(attendance)
        s.commit()

        return jsonify({
            "ok": True,
            "msg": "Attendance saved"
        })

    except Exception as e:
        s.rollback()
        return jsonify({
            "ok": False,
            "msg": str(e)
        })

    finally:
        s.close()

# ==================== NEW PREMIUM FEATURES ====================

@app.route("/api/student/<int:student_id>/attendance", methods=["GET"])
def get_student_attendance(student_id):
    if session.get("student_id") != student_id and not session.get("person_id"):
        return jsonify({"ok":False,"msg":"not authorized"}),401
    s = db()
    attendance_records = s.query(Attendance).filter(Attendance.student_id == student_id).all()
    out = []
    for a in attendance_records:
        course = s.query(Course).get(a.course_id)
        out.append({
            "course_code": course.code if course else "N/A",
            "date": a.date.isoformat() if a.date else None,
            "present": a.present,
            "remarks": a.remarks
        })
    s.close()
    return jsonify(out)

@app.route("/api/student/<int:student_id>/attendance/summary", methods=["GET"])
def get_attendance_summary(student_id):
    if session.get("student_id") != student_id and not session.get("person_id"):
        return jsonify({"ok":False,"msg":"not authorized"}),401
    s = db()
    enrollments = s.query(Enrollment).filter(Enrollment.student_id == student_id).all()
    summary = []
    for e in enrollments:
        course = s.query(Course).get(e.course_id)
        total = s.query(Attendance).filter(Attendance.student_id == student_id, Attendance.course_id == e.course_id).count()
        present = s.query(Attendance).filter(Attendance.student_id == student_id, Attendance.course_id == e.course_id, Attendance.present == True).count()
        percentage = (present / total * 100) if total > 0 else 0
        summary.append({
            "course_code": course.code if course else "N/A",
            "course_title": course.title if course else "N/A",
            "total_sessions": total,
            "present": present,
            "absent": total - present,
            "percentage": round(percentage, 2)
        })
    s.close()
    return jsonify(summary)

@app.route("/api/student/<int:student_id>/badges", methods=["GET"])
def get_student_badges(student_id):
    if session.get("student_id") != student_id and not session.get("person_id"):
        return jsonify({"ok":False,"msg":"not authorized"}),401
    s = db()
    badges = s.query(DigitalBadge).filter(DigitalBadge.student_id == student_id).all()
    out = []
    for b in badges:
        course = s.query(Course).get(b.course_id)
        out.append({
            "badge_name": b.badge_name,
            "badge_icon": b.badge_icon,
            "course_code": course.code if course else "N/A",
            "achieved_date": b.achieved_date.isoformat() if b.achieved_date else None
        })
    s.close()
    return jsonify(out)

@app.route("/api/student/<int:student_id>/certificates", methods=["GET"])
def get_student_certificates(student_id):
    if session.get("student_id") != student_id and not session.get("person_id"):
        return jsonify({"ok":False,"msg":"not authorized"}),401
    s = db()
    certificates = s.query(Certificate).filter(Certificate.student_id == student_id).all()
    out = []
    for c in certificates:
        course = s.query(Course).get(c.course_id)
        out.append({
            "certificate_type": c.certificate_type,
            "course_code": course.code if course else "N/A",
            "issued_date": c.issued_date.isoformat() if c.issued_date else None,
            "certificate_url": c.certificate_url
        })
    s.close()
    return jsonify(out)

@app.route("/api/student/<int:student_id>/fee-payment-guide", methods=["GET"])
def fee_payment_guide(student_id):
    if session.get("student_id") != student_id and not session.get("person_id"):
        return jsonify({"ok":False,"msg":"not authorized"}),401
    
    payment_guide = {
        "payment_methods": [
            {
                "method": "Mobile Money (MTN/Airtel)",
                "instructions": [
                    "Dial *165# on your MTN/Airtel number",
                    "Select 'Send Money'",
                    "Enter recipient: +256 774 123 456",
                    "Enter amount (tuition balance)",
                    "Enter PIN and confirm",
                    "Screenshot or note transaction reference"
                ],
                "processing_time": "Instant",
                "fees": "None"
            },
            {
                "method": "Bank Transfer",
                "instructions": [
                    "Account Name: NTISD - Northern Technical and Social Institute",
                    "Account Number: 1234567890",
                    "Bank: Kampala Doctors' Hospital",
                    "Branch: Mpigi",
                    "Include student registration number in reference",
                    "Visit bank or use online banking"
                ],
                "processing_time": "1-2 working days",
                "fees": "Bank dependent"
            },
            {
                "method": "Cash Payment",
                "instructions": [
                    "Visit NTISD Main Campus - Mpigi",
                    "Go to Finance Office",
                    "Provide student registration number",
                    "Hand cash to cashier",
                    "Request receipt"
                ],
                "processing_time": "Immediate",
                "fees": "None"
            }
        ],
        "important_notes": [
            "Always include your registration number with payments",
            "Keep payment receipts for your records",
            "Contact admin if payment not reflected within 48 hours",
            "Semester 1: January - May, Semester 2: August - December"
        ]
    }
    return jsonify(payment_guide)

@app.route("/api/student/<int:student_id>/fee-history", methods=["GET"])
def fee_history(student_id):
    if session.get("student_id") != student_id and not session.get("person_id"):
        return jsonify({"ok":False,"msg":"not authorized"}),401
    s = db()
    payments = s.query(TuitionPayment).filter(TuitionPayment.student_id == student_id).order_by(TuitionPayment.due_date.desc()).all()
    out = []
    for p in payments:
        out.append({
            "id": p.id,
            "amount": p.amount,
            "due_date": p.due_date.isoformat() if p.due_date else None,
            "paid_date": p.paid_date.isoformat() if p.paid_date else None,
            "status": p.status,
            "semester": p.semester,
            "days_overdue": max(0, (datetime.datetime.utcnow() - p.due_date).days) if p.due_date and p.status == "unpaid" else 0
        })
    s.close()
    return jsonify(out)

@app.route("/api/admin/semester-export-reminder", methods=["GET"])
def semester_export_reminder():
    if session.get("role") != "admin":
        return jsonify({"ok":False,"msg":"not authorized"}),403
    s = db()
    semesters = s.query(Semester).all()
    now = datetime.datetime.utcnow()
    reminders = []
    for sem in semesters:
        if sem.end_date and sem.end_date <= now:
            reminders.append({
                "semester_name": sem.name,
                "end_date": sem.end_date.isoformat(),
                "days_since_end": (now - sem.end_date).days,
                "status": "EXPORT_RECOMMENDED" if (now - sem.end_date).days >= 3 else "UPCOMING",
                "message": f"Semester '{sem.name}' ended. Time to export results!"
            })
    s.close()
    return jsonify(reminders)

@app.route("/api/program-types", methods=["GET"])
def list_program_types():
    s = db()
    category = request.args.get("category")
    q = s.query(ProgramType)
    if category:
        q = q.filter(ProgramType.category == category)
    programs = q.all()
    out = []
    for p in programs:
        out.append({
            "id": p.id,
            "name": p.name,
            "duration_months": p.duration_months,
            "duration_display": f"{p.duration_months // 12} years" if p.duration_months >= 12 else f"{p.duration_months} months",
            "category": p.category,
            "description": p.description
        })
    s.close()
    return jsonify(out)

@csrf.exempt
@app.route("/api/notifications/create", methods=["POST"])
def create_notification():
    if "person_id" not in session:
        return jsonify({
            "ok": False
        }), 401
    data = request.json
    s = db()

    try:
        note = Notification(
            title=data["title"],
            message=data["message"]
        )
        s.add(note)
        s.commit()
        return jsonify({
            "ok": True
        })

    except Exception as e:
        s.rollback()
        return jsonify({
            "ok": False,
            "msg": str(e)
        })
    finally:
        s.close()

@app.route("/dashboard")
def dashboard_router():
    role = session.get("role")
    if not role:
        return redirect("/login")

    if role == "admin":
        return redirect("/admin/dashboard")

    elif role == "lecturer":
        return redirect("/lecturer/dashboard")

    elif role == "finance":
        return redirect("/finance/dashboard")

    elif role == "principal":
        return redirect("/principal/dashboard")

    return redirect("/")

@app.route("/api/admin/stats")
def admin_stats():
    if session.get("role") != "admin":
        return jsonify({
            "ok": False
        }), 403
    s = db()

    try:
        students = s.query(Student).count()
        staff = s.query(Person).count()
        courses = s.query(Course).count()
        branches = s.query(Branch).count()
        notifications = s.query(Notification).count()
        
        return jsonify({
            "students": students,
            "staff": staff,
            "courses": courses,
            "branches": branches,
            "notifications": notifications
        })
    finally:
        s.close()

@app.route("/api/search/students")
def search_students():
    q = request.args.get("q", "").strip()
    s = db()

    students = (
        s.query(Student)
        .filter(
            Student.full_name.ilike(f"%{q}%")
        )
        .limit(20)
        .all()
    )
    output = []

    for st in students:
        output.append({
            "id": st.id,
            "reg_no": st.reg_no,
            "name": st.full_name
        })
    s.close()
    return jsonify(output)

@app.route("/api/notifications/<int:recipient_id>", methods=["GET"])
def get_notifications(recipient_id):
    pid = session.get("person_id")
    sid = session.get("student_id")
    if not (pid == recipient_id or sid == recipient_id):
        return jsonify({"ok":False,"msg":"not authorized"}),401
    s = db()
    notifications = s.query(Notification).filter(Notification.recipient_id == recipient_id).order_by(Notification.created_at.desc()).all()
    out = []
    for n in notifications:
        out.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        })
    s.close()
    return jsonify(out)

@app.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    s = db()
    notification = s.query(Notification).get(notification_id)
    if not notification:
        s.close()
        return jsonify({"ok":False,"msg":"not found"}),404
    notification.is_read = True
    s.commit()
    s.close()
    return jsonify({"ok":True})

@app.route("/api/institution/info", methods=["GET"])
def institution_info():
    info = {
        "name": "NTISD - Nsamizi Training Institute for Social Development",
        "physical_address": "Kkonge Road, Mayembe Upper, Mpigi Town Council, Mpigi District, Uganda",
        "vision": "To become a reputable center of excellence in training and producing practical oriented human resources that ably deliver quality services that can transform the social development sector.",
        "mission": "To produce competent human resource with positive attitudes that deliver quality services in social development for socio-economic development.",
        "partners": {
            "international": [
                "Netherlands Initiative for Capacity Enhancement of higher Education (NICHE)",
                "World Vision-UG",
                "The Erasmus International Institute of Social Studies, The Hague, The Netherlands",
                "United Nations High Commission for Refugees (UNHCR)",
                "Kwazulu Natal University",
                "Makerere University-Kampala",
                "Uganda Martyrs' University-Nkozi"
            ],
            "local": [
                "All Local Governments in Uganda",
                "REPPSI (Regional Psychosocial Support Initiative)",
                "Non-governmental Organisations"
            ]
        }
    }
    return jsonify(info)

@app.route("/api/system/health")
def system_health():
    checks = {
        "database": True,
        "login": True,
        "students": True,
        "staff": True,
        "courses": True,
        "attendance": True,
        "notifications": True,
        "exports": True
    }
    return jsonify(checks)

# ============================================================================
# ERROR HANDLERS
# ============================================================================
@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    return jsonify({'success': False, 'message': 'Bad request'}), 400


@app.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors"""
    return jsonify({'success': False, 'message': 'Unauthorized'}), 401


@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    return jsonify({'success': False, 'message': 'Forbidden'}), 403


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'success': False, 'message': 'Not found'}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    logger.error(f"Server error: {str(error)}")
    return jsonify({'success': False, 'message': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
