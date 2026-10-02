# PostgreSQL Setup & Migration Guide
## Nsamizi Digital Fortress - Production Database Setup

**Date**: May 9, 2026
**Purpose**: Complete PostgreSQL database setup with data migration from SQLite
**Status**: Ready for Implementation

---
## 🎯 Overview
This guide provides step-by-step instructions to:
1. Create PostgreSQL database and user
2. Migrate data from SQLite to PostgreSQL
3. Update Flask app configuration
4. Verify data integrity
5. Test with PostgreSQL

---
## 📋 Prerequisites
### Windows Users (You!)
- ✅ PostgreSQL 18.3 installed (you have this!)
- ✅ psql command available in PATH
- ✅ Python with SQLAlchemy installed
- ✅ Your Flask app (app-1.py)

### Verification
Run this command to verify PostgreSQL:
```
psql -U postgres --version
```
Expected output: `psql (PostgreSQL) 18.3`

---
## 🚀 Step 1: Create PostgreSQL Database & User
### Using Command Line (psql)
Open your terminal and run:
```sql
-- Connect to PostgreSQL as admin
psql -U postgres

-- Create database
CREATE DATABASE nsamizi_db;

-- Create user
CREATE USER nsamizi_user WITH PASSWORD 'your_secure_password_here';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE nsamizi_db TO nsamizi_user;

-- Connect to the database
\c nsamizi_db

-- Grant schema privileges
GRANT ALL PRIVILEGES ON SCHEMA public TO nsamizi_user;
GRANT CREATE ON SCHEMA public TO nsamizi_user;

-- Exit
\q
```

### Quick Command (Copy-Paste)
```bash
psql -U postgres -c "CREATE DATABASE nsamizi_db;"
psql -U postgres -c "CREATE USER nsamizi_user WITH PASSWORD 'Nsamizi@Secure2026';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE nsamizi_db TO nsamizi_user;"
psql -U postgres -d nsamizi_db -c "GRANT ALL PRIVILEGES ON SCHEMA public TO nsamizi_user;"
```

---

## 🔄 Step 2: Update Flask Configuration
### Update config.json
Edit `C:\Users\Will_Newton\Desktop\Nsamizi full demo\config.json`:
```json
{
  "DB_URL": "postgresql://nsamizi_user:Nsamizi@Secure2026@localhost:5432/nsamizi_db",
  "SECRET_KEY": "your-secret-key-nsamizi-2026",
  "DEMO_BRANCHES": ["Adjumani", "Gulu", "Nsambya", "Kampala", "Mpigi", "Kasese", "Lira"]
}
```

### Environment Variables (Alternative - More Secure)
Create a `.env` file in your app directory:
```bash
DATABASE_URL=postgresql://nsamizi_user:Nsamizi@Secure2026@localhost:5432/nsamizi_db
SECRET_KEY=your-secret-key-nsamizi-2026
FLASK_ENV=production
```

Then update app-1.py to load from environment:
```python
from dotenv import load_dotenv
import os

load_dotenv()
DB_URL = os.environ.get("DATABASE_URL", CFG.get("DB_URL"))
SECRET_KEY = os.environ.get("SECRET_KEY", CFG.get("SECRET_KEY"))
```

---

## 🔀 Step 3: Automatic Schema Creation
When you run Flask with PostgreSQL, it will automatically create all tables. The best approach:
### Method 1: Let Flask Create Schema (Recommended)
1. Update config.json with PostgreSQL URL
2. Stop any running Flask app
3. Delete SQLite database (optional, for clean start)
4. Run Flask app:

```bash
cd "C:\Users\Will_Newton\Desktop\Nsamizi full demo"
python app-1.py
```

The app will:
- Detect PostgreSQL database is empty
- Create all tables automatically
- Seed demo data
- Ready for use

### Method 2: Export/Import (For Existing Data)
If you want to preserve SQLite data:
```bash
# Step 1: Dump SQLite to SQL
sqlite3 nsamizi_demo.db .dump > sqlite_dump.sql

# Step 2: Adapt the SQL for PostgreSQL (manual editing needed)
# Step 3: Import to PostgreSQL
psql -U nsamizi_user -d nsamizi_db -f sqlite_dump.sql
```

---
## ✅ Step 4: Verification
### Test Database Connection
Create a test script: `test_db.py`

```python
from sqlalchemy import create_engine, text

# PostgreSQL connection
db_url = "postgresql://nsamizi_user:Nsamizi@Secure2026@localhost:5432/nsamizi_db"
engine = create_engine(db_url, echo=False, future=True)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ PostgreSQL Connection Successful!")
        print(f"Database: nsamizi_db")
        print(f"User: nsamizi_user")
        print(f"Server: localhost:5432")
except Exception as e:
    print(f"❌ Connection Failed: {e}")

# List all tables
try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema='public'
        """))
        tables = result.fetchall()
        print(f"\n✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
except Exception as e:
    print(f"❌ Error listing tables: {e}")
```

Run it:
```bash
python test_db.py
```

Expected output:
```
✅ PostgreSQL Connection Successful!
Database: nsamizi_db
User: nsamizi_user
Server: localhost:5432

✅ Found 11 tables:
  - branches
  - people
  - students
  - courses
  - teaches
  - enrollments
  - assessments
  - marks
  - audit_log
  - login_attempts
  - tuition_payments
  - bible_quotes
  - semesters
```

### Query Sample Data
```sql
-- Connect to PostgreSQL
psql -U nsamizi_user -d nsamizi_db

-- Check students
SELECT COUNT(*) FROM students;

-- Check branches
SELECT * FROM branches;

-- Check demo users
SELECT full_name, role, email FROM people LIMIT 5;

-- Exit
\q
```

---
## 🧪 Step 5: Test Flask App with PostgreSQL
### Run the App
```bash
cd "C:\Users\Will_Newton\Desktop\Nsamizi full demo"
python app-1.py
```

### Test Login
1. Navigate to http://127.0.0.1:5000
2. Click "Login to System"
3. Test as Student:
   - Role: Student
   - Reg#: NS2025-000000001
   - Password: Aisha#2025
   - Should see student dashboard

4. Test as Lecturer:
   - Role: Lecturer
   - Email: alice@nsamizi
   - Password: Alice@123
   - Should see staff dashboard

### Check Application Logs
Monitor terminal output for any errors:
```
[ERROR] Database connection failed
[WARNING] Migration issue
[SUCCESS] Data loaded successfully
```
---

## 🔐 Step 6: Security Configuration
### Update Passwords in Production
```sql
-- Connect as admin
psql -U postgres -d nsamizi_db

-- Change nsamizi_user password
ALTER USER nsamizi_user WITH PASSWORD 'new_very_secure_password_here';

-- Exit
\q
```

### Restrict User Permissions
```sql
psql -U postgres -d nsamizi_db

-- Revoke public access
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- Grant only necessary privileges
GRANT USAGE ON SCHEMA public TO nsamizi_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nsamizi_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO nsamizi_user;

-- Exit
\q
```

---
## 🔄 Step 7: Migration Checklist
- [ ] PostgreSQL 18.3 installed and running
- [ ] Database `nsamizi_db` created
- [ ] User `nsamizi_user` created with password
- [ ] Privileges granted to user
- [ ] config.json updated with PostgreSQL URL
- [ ] Flask app starts without errors
- [ ] Database connection test passes
- [ ] All tables created in PostgreSQL
- [ ] Demo data seeded successfully
- [ ] Student login works
- [ ] Lecturer login works
- [ ] Marks display correctly
- [ ] Bible quotes work
- [ ] Tuition status shows
- [ ] All pages load without errors

---
## 🆘 Troubleshooting
### Error: "could not connect to server"
**Problem**: PostgreSQL not running
**Solution**:
```bash
# Check if PostgreSQL service is running
Get-Service postgresql-*

# Start PostgreSQL if stopped
Start-Service postgresql-x64-18
```

### Error: "FATAL: Ident authentication failed"
**Problem**: Password authentication issue
**Solution**:
```bash
# Use psql with explicit password
psql -U nsamizi_user -d nsamizi_db -W
# Then enter password when prompted
```

### Error: "database nsamizi_db does not exist"
**Problem**: Database not created
**Solution**:
```bash
# Create database
psql -U postgres -c "CREATE DATABASE nsamizi_db;"
```

### Error: "permission denied for database nsamizi_db"
**Problem**: Permissions not granted
**Solution**:
```bash
psql -U postgres -d nsamizi_db -c "GRANT ALL PRIVILEGES ON DATABASE nsamizi_db TO nsamizi_user;"
```

### Tables not appearing
**Problem**: Flask didn't create schema
**Solution**:
```python
# Run in Python shell:
from app import Base, engine
Base.metadata.create_all(engine)
print("✅ All tables created!")
```

---
## 📊 Verification Queries
Run these to verify everything works:
```sql
-- Check student count
SELECT COUNT(*) as student_count FROM students;

-- Check if marks exist
SELECT COUNT(*) as marks_count FROM marks;

-- Check fee records
SELECT COUNT(*) as fee_count FROM tuition_payments;

-- Check Bible quotes
SELECT COUNT(*) as quote_count FROM bible_quotes;

-- Check all people
SELECT role, COUNT(*) as count FROM people GROUP BY role;
```

---
## 🎯 Next Steps After Migration
1. **Backup Strategy**
   - Set up daily PostgreSQL backups
   - Use backup.py script (updated for PostgreSQL)
   - Store backups securely

2. **Performance Tuning**
   - Create indexes for frequently queried columns
   - Optimize queries
   - Monitor database performance

3. **Security Hardening**
   - Enable SSL connections
   - Set up firewall rules
   - Implement backup encryption

4. **Monitoring**
   - Set up database monitoring
   - Log all connections
   - Alert on unusual activity
---

## 📝 Updated app-1.py Configuration
After migration, your app will use this:
```python
# For PostgreSQL
DB_URL = "postgresql://nsamizi_user:Nsamizi@Secure2026@localhost:5432/nsamizi_db"

# Or with environment variable
import os
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///nsamizi_demo.db")

# SQLAlchemy will handle the switch
engine = create_engine(DB_URL, echo=False, future=True)
```

---
## ✅ Success Indicators
When PostgreSQL migration is complete, you'll see:
✅ All 13 tables created in `nsamizi_db`
✅ Demo data (11 staff + 2 students) loaded
✅ All login roles working
✅ Marks displaying correctly
✅ Bible quotes working
✅ Tuition status tracking
✅ All pages loading without errors
✅ Performance faster than SQLite
✅ Ready for production use

---

## 📞 Quick Reference
```bash
# Connect to PostgreSQL as admin
psql -U postgres

# Connect as app user
psql -U nsamizi_user -d nsamizi_db -W

# List databases
\l

# List tables
\dt

# Show database size
SELECT pg_database.datname,
       pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database;

# Exit psql
\q
```
---

## 🎉 PostgreSQL Ready!
Your system is now running on enterprise-grade PostgreSQL instead of SQLite.
**Benefits**:
- ✅ Better performance
- ✅ Multi-user support
- ✅ Better security
- ✅ Production ready
- ✅ Scalability
- ✅ Advanced features

**Version**: PostgreSQL 18.3
**Database**: nsamizi_db
**User**: nsamizi_user
**Status**: ✅ Ready for Production

---
**Last Updated**: May 9, 2026
**PostgreSQL Version**: 18.3
**Schema Version**: 1.0
