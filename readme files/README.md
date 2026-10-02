# Nsamizi-Digital-Fortress
A comprehensive tracking system for Nsamizi Institute, built with Flask and PostgreSQL/SQLite.

## Features
- **User Management**: Separate logins for students, lecturers, coordinators, principals, and admins with role-based access.
- **Course Tracking**: Supports Diploma (2 years) and Degree (3 years) programs with semester-based results.
- **Marks Management**: Lecturers can input marks, system generates comments based on performance.
- **Tuition Payment Tracking**: Tracks payments, shows status, reminders for unpaid fees (set to UGX 1,200,000).
- **Bible Quotes**: Daily inspirational quotes displayed on all dashboards.
- **Admin Panel**: System overview, login logs, suspicious activity monitoring.
- **Security**: Brute-force protection (3 failed logins block for 24 hours), bcrypt password hashing, parameterized queries.
- **Data Export**: Excel files for semester results, readonly for non-admins.
- **Backup & Recovery**: Automated scripts for system backup and restoration.

## Installation
1. **Install Python Dependencies**:
   ```
   pip install flask sqlalchemy bcrypt pandas openpyxl psycopg2-binary
   ```
   - `flask`: Web framework for routing and templates.
   - `sqlalchemy`: ORM for database interactions.
   - `bcrypt`: Secure password hashing.
   - `pandas` & `openpyxl`: For Excel export functionality.
   - `psycopg2-binary`: PostgreSQL driver.

2. **Database Setup**:
   - **SQLite (Default for Demo)**: No setup required, uses local file `nsamizi_demo.db`.
   - **PostgreSQL (Production)**:
     1. Install PostgreSQL server.
     2. Create database: `createdb nsamizi_db`
     3. Create user: `createuser nsamizi_user`
     4. Set password and grant permissions: `GRANT ALL PRIVILEGES ON DATABASE nsamizi_db TO nsamizi_user;`
     5. Update `config.json` or environment: `DB_URL=postgresql://nsamizi_user:password@localhost/nsamizi_db`

3. **Configuration**:
   - Create `config.json` or set environment variables:
     - `DB_URL`: Database connection string.
     - `SECRET_KEY`: Flask session secret.
     - `DEMO_BRANCHES`: List of center names for seeding.

4. **Run the Application**:
   ```
   python app-1.py
   ```
   - Seeds demo data on first run.
   - Starts on http://127.0.0.1:5000

## Usage
- **Home Page**: Link to login.
- **Login Page**: Select role, enter email/reg_no and password.
- **Student Dashboard**: View courses, marks, tuition status, Bible quote.
- **Lecturer Dashboard**: View courses, students, input marks.
- **Coordinator Dashboard**: View results and tuition for their center (coordinators) or all (overall coordinators).
- **Principal Dashboard**: View all centers, staff, performance.
- **Admin Dashboard**: System stats, logs, exports.

## Code Structure
- `app-1.py`: Main Flask app with routes, models, and logic.
  - Models: Branch, Person, Student, Course, etc. with relationships.
  - Routes: API endpoints for login, data fetching, updates.
  - Security: Login attempts tracking, blocking.
- `templates/`: HTML templates using custom CSS.
- `static/`: CSS, JS, images.
- `backup.py`: Backs up DB and files.
- `recover.py`: Restores from backup.

## Security Measures
- **Password Hashing**: Uses bcrypt for secure storage.
- **Brute-Force Protection**: Tracks failed logins, blocks account for 24 hours after 3 failures.
- **Parameterized Queries**: Prevents SQL injection.
- **Audit Logging**: Logs all actions, especially suspicious ones.
- **Session Management**: Flask sessions for authentication.

## Backup & Recovery
- **Backup**: `python backup.py` creates timestamped directory with DB dump/files.
- **Recovery**: `python recover.py <backup_dir>` restores DB and files.

## Production Deployment
- Use Gunicorn or similar WSGI server.
- Set up PostgreSQL.
- Use environment variables for secrets.
- Enable HTTPS.
- Regular backups.

## Demo Credentials
- Student: reg_no=NS2025-000000001, password=Aisha#2025
- Lecturer: email=alice@nsamizi, password=Alice@123
- Admin: email=admin@nsamizi, password=Admin@123