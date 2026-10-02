from app import db, Person, Student
from bcrypt import hashpw, gensalt

s = db()

new_hash = hashpw(
    "DemoPass@2025".encode("utf-8"),
    gensalt()
).decode("utf-8")

people = s.query(Person).all()

for p in people:
    p.password_hash = new_hash
    p.failed_login_count = 0
    p.blocked_until = None

students = s.query(Student).all()

for st in students:
    st.password_hash = new_hash
    st.failed_login_count = 0
    st.blocked_until = None

s.commit()

print("RESET DONE")

s.close()