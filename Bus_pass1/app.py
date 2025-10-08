# app.py

import os
import uuid
import qrcode
import datetime
from PIL import Image
import mysql.connector  # Using the standard MySQL connector
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

# --- CONFIGURATION ---
# Note: config.py must exist in the same directory and contain DB and SECRET_KEY variables
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

# File Upload Settings
UPLOAD_FOLDER = 'static/uploads'
PHOTO_FOLDER = os.path.join(UPLOAD_FOLDER, 'photos')
QR_CODE_FOLDER = os.path.join(UPLOAD_FOLDER, 'qrcodes')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directories exist
os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(QR_CODE_FOLDER, exist_ok=True)


# --- DATABASE CONNECTION HELPER FUNCTION (FIXED) ---
def get_db_connection():
    """
    Establishes a connection to the MySQL database using mysql.connector.
    This replaces the outdated flaskext.mysql functionality.
    """
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
        # Cannot call flash here reliably if not in request context in other situations, but leaving an informative print
        return None


# --- HELPER FUNCTIONS ---
def is_logged_in():
    """Checks if a user session is active."""
    return 'user_id' in session


def is_admin_logged_in():
    """Checks if an admin session is active."""
    return 'admin_id' in session


def generate_qr_code(data: str, filename: str) -> str:
    """
    Generates a QR code image file in QR_CODE_FOLDER and returns the DB-relative path
    (eg. 'uploads/qrcodes/<filename>.png') for storing in the database.
    """
    full_path = os.path.join(QR_CODE_FOLDER, filename)
    # Using qrcode make and save
    img = qrcode.make(data)
    img.save(full_path)
    # Return path relative to 'static' for use in templates: 'uploads/qrcodes/filename'
    return os.path.join('uploads', 'qrcodes', filename).replace('\\', '/')


# Random Bangalore Points for Pass Application (Simulated data)
BANGALORE_POINTS = [
    "Majestic", "Jayanagar", "Whitefield", "Koramangala",
    "Electronic City", "Indiranagar", "Marathahalli", "Yeshwanthpur"
]


# --- USER ROUTES ---
@app.route('/')
def index():
    if is_logged_in():
        # Redirect logged-in users to the application page
        return redirect(url_for('apply_pass'))
    return render_template('public/index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        address = request.form.get('address')
        phone_number = request.form.get('phone_number')
        photo = request.files.get('photo')

        if not all([name, email, password, phone_number]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('public/register.html')

        # Hash password using Werkzeug security
        password_hash = generate_password_hash(password)
        photo_path = None
        conn = get_db_connection()

        if not conn:
            flash("Database connection failed. Please try later.", "danger")
            return render_template('public/register.html')

        try:
            cursor = conn.cursor()

            # 1. Handle photo upload (optional)
            if photo and photo.filename != '':
                # Create a unique filename
                photo_filename = str(uuid.uuid4()) + os.path.splitext(photo.filename)[-1]

                # Check extension (basic security)
                if photo_filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    photo_file_path = os.path.join(PHOTO_FOLDER, photo_filename)
                    photo.save(photo_file_path)
                    # Store relative path for serving via static route
                    photo_path = os.path.join('uploads', 'photos', photo_filename).replace('\\', '/')
                else:
                    flash('Invalid file type for photo.', 'danger')
                    return render_template('public/register.html')

            # 2. Insert user data
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, address, phone_number, photo_path) VALUES (%s, %s, %s, %s, %s, %s)",
                (name, email, password_hash, address, phone_number, photo_path)
            )
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

        except mysql.connector.Error as err:
            # MySQL error code for Duplicate Entry is 1062
            if getattr(err, 'errno', None) == 1062:
                flash('This email address is already registered.', 'danger')
            else:
                flash(f'An unexpected database error occurred: {err}', 'danger')
            return render_template('public/register.html')
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            conn.close()

    return render_template('public/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        if not conn:
            flash("Database connection failed. Please try later.", "danger")
            return render_template('public/login.html')

        # Use dictionary=True to fetch results as dictionaries
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if user and check_password_hash(user['password_hash'], password):
            # Set session variables
            session['user_id'] = user['id']
            session['email'] = email
            flash('Login successful!', 'success')
            return redirect(url_for('apply_pass'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('public/login.html')


@app.route('/apply_pass', methods=['GET', 'POST'])
def apply_pass():
    if not is_logged_in():
        flash('Please log in to apply for a pass.', 'warning')
        return redirect(url_for('login'))

    # Hardcoded/Simulated Pass Amount
    PASS_AMOUNT = 500.00

    conn = get_db_connection()
    if not conn:
        flash("Database connection failed. Please try later.", "danger")
        return render_template('public/apply_pass.html', points=BANGALORE_POINTS, amount=PASS_AMOUNT, latest_app=None)

    cursor = conn.cursor(dictionary=True)

    # Fetch latest application status
    try:
        cursor.execute(
            "SELECT id, status, payment_status, start_point, end_point FROM applications WHERE user_id = %s ORDER BY application_date DESC LIMIT 1",
            (session['user_id'],)
        )
        latest_application = cursor.fetchone()
    except Exception as e:
        app.logger.error(f"Error fetching latest application: {e}")
        latest_application = None

    if request.method == 'POST':
        start_point = request.form.get('start_point')
        end_point = request.form.get('end_point')

        # Save application and redirect to payment
        try:
            # Re-check pending payment using latest_application
            if latest_application and latest_application.get('payment_status') == 'PENDING' and latest_application.get('status') != 'REJECTED':
                flash('You have a pending application awaiting payment. Please complete the previous payment.', 'warning')
                cursor.close()
                conn.close()
                return redirect(url_for('payment', app_id=latest_application['id']))

            cursor.execute(
                "INSERT INTO applications (user_id, start_point, end_point, amount, status, payment_status, application_date) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                (session['user_id'], start_point, end_point, PASS_AMOUNT, 'PENDING', 'PENDING')
            )
            conn.commit()
            application_id = cursor.lastrowid

            flash('Application submitted! Proceed to payment.', 'info')
            return redirect(url_for('payment', app_id=application_id))
        except Exception as e:
            flash(f"Error submitting application: {e}", 'danger')
            app.logger.error(f"Application Submission Error: {e}")
        finally:
            cursor.close()
            conn.close()

    cursor.close()
    conn.close()
    return render_template(
        'public/apply_pass.html',
        points=BANGALORE_POINTS,
        amount=PASS_AMOUNT,
        latest_app=latest_application
    )


@app.route('/payment/<int:app_id>', methods=['GET', 'POST'])
def payment(app_id):
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        flash("Database connection failed. Please try later.", "danger")
        return redirect(url_for('apply_pass'))

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM applications WHERE id = %s AND user_id = %s",
            (app_id, session['user_id'])
        )
        application = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not application:
        flash('Invalid application ID.', 'warning')
        return redirect(url_for('apply_pass'))

    if application.get('payment_status') == 'COMPLETED':
        flash('Payment already completed for this application.', 'info')
        return redirect(url_for('digital_pass'))

    if request.method == 'POST':
        # --- PAYMENT GATEWAY SIMULATION ---
        conn2 = get_db_connection()
        if not conn2:
            flash("Database connection failed. Please try later.", "danger")
            return redirect(url_for('apply_pass'))

        try:
            cursor_update = conn2.cursor()
            cursor_update.execute(
                "UPDATE applications SET payment_status = 'COMPLETED', status = 'PENDING' WHERE id = %s",
                (app_id,)
            )
            conn2.commit()
            flash('Payment successful! Your application is now pending admin review.', 'success')
            cursor_update.close()
            return redirect(url_for('digital_pass'))  # Redirect to check status
        except Exception as e:
            flash(f"Payment update error: {e}", 'danger')
            app.logger.error(f"Payment Update Error: {e}")
        finally:
            try:
                cursor_update.close()
            except Exception:
                pass
            conn2.close()

    return render_template('public/payment.html', application=application)


@app.route('/digital_pass')
def digital_pass():
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        flash("Database connection failed. Please try later.", "danger")
        return render_template('public/digital_pass.html', pass_data=None)

    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch approved pass details (most recent approved pass)
        cursor.execute("""
                       SELECT a.*,
                              u.name,
                              u.phone_number,
                              u.photo_path
                       FROM applications a
                                JOIN users u ON a.user_id = u.id
                       WHERE a.user_id = %s
                         AND a.status = 'APPROVED'
                       ORDER BY a.application_date DESC LIMIT 1
                       """, (session['user_id'],))

        approved_pass = cursor.fetchone()

        # Fetch latest overall application status for context
        cursor.execute(
            "SELECT status, payment_status FROM applications WHERE user_id = %s ORDER BY application_date DESC LIMIT 1",
            (session['user_id'],)
        )
        latest_status = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not approved_pass:
        if latest_status:
            flash(
                f'Your latest application status: {latest_status.get("status")} (Payment: {latest_status.get("payment_status")}).',
                'info')
        else:
            flash('No approved pass found. Please apply for a pass.', 'warning')
        return redirect(url_for('apply_pass'))

    return render_template('public/digital_pass.html', pass_data=approved_pass)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# --- ADMIN ROUTES ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        if not conn:
            flash("Database connection failed. Please try later.", "danger")
            return render_template('admin/admin_login.html')

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, password_hash FROM admin_users WHERE username = %s", (username,))
            admin = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        # Security Note: In a real system, use check_password_hash here.
        # Since the SQL blueprint didn't use hashing for the default admin,
        # we check the plain password stored in the database for simplicity of setup.
        if admin and admin.get('password_hash') == password:
            session['admin_id'] = admin['id']
            session['admin_username'] = username
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('admin/admin_login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    if not db:
        flash("Database connection failed. Please try later.", "danger")
        return render_template('admin/dashboard.html', pending_count=0)

    cursor = db.cursor()
    pending_count = 0
    try:
        # Count applications that have paid but are awaiting review
        cursor.execute("SELECT COUNT(id) FROM applications WHERE payment_status = 'COMPLETED' AND status = 'PENDING'")
        row = cursor.fetchone()
        pending_count = row[0] if row else 0
    except mysql.connector.Error as err:
        app.logger.error(f"DB Error fetching pending count: {err}")
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        db.close()

    return render_template('admin/dashboard.html', pending_count=pending_count)


@app.route('/admin/applications')
def admin_applications():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    if not db:
        flash("Database connection failed. Please try later.", "danger")
        return render_template('admin/applications.html', applications=[])

    cursor = db.cursor(dictionary=True)
    applications = []

    try:
        # Fetch all applications that have been paid (COMPLETED)
        cursor.execute(
            """
            SELECT a.*, u.name, u.email, u.phone_number
            FROM applications a
            JOIN users u ON a.user_id = u.id
            WHERE a.payment_status = 'COMPLETED'
            ORDER BY a.application_date ASC
            """
        )
        applications = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f'Database Error fetching applications: {getattr(err, "msg", err)}', 'danger')
        app.logger.error(f"DB Error fetching applications: {err}")
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        db.close()

    return render_template('admin/applications.html', applications=applications)


@app.route('/admin/process_pass/<int:app_id>/<string:action>')
def process_pass(app_id, action):
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    db = get_db_connection()
    if not db:
        flash("Database connection failed. Please try later.", "danger")
        return redirect(url_for('admin_applications'))

    cursor = db.cursor(dictionary=True)

    try:
        # Fetch application and related user details first
        cursor.execute(
            """
            SELECT a.*, u.name AS user_name, u.email AS user_email, u.phone_number AS user_phone, u.photo_path AS user_photo
            FROM applications a
            JOIN users u ON a.user_id = u.id
            WHERE a.id = %s
            """,
            (app_id,)
        )
        app_data = cursor.fetchone()
        if not app_data:
            flash(f'Application ID {app_id} not found.', 'warning')
            return redirect(url_for('admin_applications'))

        if action == 'reject':
            try:
                cursor.execute(
                    "UPDATE applications SET status = %s, pass_number = NULL, qr_code_path = NULL WHERE id = %s",
                    ('REJECTED', app_id)
                )
                db.commit()
                flash(f'Application {app_id} has been REJECTED.', 'warning')
            except mysql.connector.Error as err:
                db.rollback()
                flash(f"Error rejecting application: {getattr(err, 'msg', err)}", 'danger')
                app.logger.error(f"DB Error rejecting application {app_id}: {err}")
            return redirect(url_for('admin_applications'))

        if action == 'approve':
            try:
                # 1. Generate Pass Number
                pass_number = f"BP-{app_id}-{datetime.datetime.now().strftime('%Y%m%d')}"

                # Fallback if start/end not present
                start_point = app_data.get('start_point', 'NA')
                end_point = app_data.get('end_point', 'NA')

                # 2. Data for QR Code
                qr_data = f"PASS_NO:{pass_number}|USER:{app_data.get('user_name')}|ROUTE:{start_point}-{end_point}|STATUS:APPROVED"
                qr_filename = f"{pass_number}.png"
                qr_code_db_path = generate_qr_code(qr_data, qr_filename).replace('\\', '/')

                # 3. Update Application in DB to APPROVED
                cursor.execute(
                    "UPDATE applications SET status = %s, pass_number = %s, qr_code_path = %s WHERE id = %s",
                    ('APPROVED', pass_number, qr_code_db_path, app_id)
                )
                db.commit()
                flash(f'Pass for Application ID {app_id} approved, pass number {pass_number} generated.', 'success')
            except mysql.connector.Error as err:
                db.rollback()
                flash(f'Error approving pass: {getattr(err, "msg", err)}', 'danger')
                app.logger.error(f"DB Error during pass approval: {err}")
            except Exception as e:
                db.rollback()
                flash(f'Unexpected error during approval: {e}', 'danger')
                app.logger.error(f"Unexpected error during pass approval: {e}")
            finally:
                return redirect(url_for('admin_applications'))

        flash('Invalid action.', 'danger')
        return redirect(url_for('admin_applications'))

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        db.close()


@app.route('/static/uploads/<path:filename>')
def serve_uploaded_files(filename):
    """
    Serves files from the UPLOAD_FOLDER (photos, qrcodes).
    """
    # This route helps access the files saved in static/uploads/
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    # Run the application
    app.run(debug=True)
