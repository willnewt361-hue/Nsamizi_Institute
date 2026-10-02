from app import db, Person, Student, hash_password

s = db()

# Reset staff passwords
users = s.query(Person).all()

for u in users:
    u.password_hash = hash_password("DemoPass@2025")
    u.failed_login_count = 0
    u.blocked_until = None

# Reset student passwords
students = s.query(Student).all()

for st in students:
    st.password_hash = hash_password("DemoPass@2025")
    st.failed_login_count = 0
    st.blocked_until = None

s.commit()
s.close()

print("All passwords reset successfully.")