import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, EmailField, TextAreaField, SubmitField, SelectField, DateField, TimeField
from wtforms.validators import DataRequired, Email
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json

# For SocketIO
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.secret_key = 'super_secret_session_key_change_this_in_production'
DB_FILE = 'database.db'

# File uploading Config
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# Flask-Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'nadipallisudharshan@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'grha zhrj tknt gthb')
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

# Flask-SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Form setup
class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    attachment = FileField('Attachment (Optional, Max 100MB)')
    submit = SubmitField('Send Message')

class LeaveForm(FlaskForm):
    leave_type = SelectField('Leave Type', choices=[('Sick', 'Sick Leave'), ('Vacation', 'Vacation'), ('Personal', 'Personal'), ('Other', 'Other')], validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[DataRequired()])
    submit = SubmitField('Submit Leave Request')

class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[DataRequired()])
    assigned_to = StringField('Assigned To (Username)', validators=[DataRequired()])
    submit = SubmitField('Create Task')

class MeetingForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    meeting_date = DateField('Date', validators=[DataRequired()])
    meeting_time = TimeField('Time', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    participants = StringField('Participants (comma separated usernames)', validators=[DataRequired()])
    submit = SubmitField('Schedule Meeting')

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_unread_message_count():
    conn = get_db_connection()

    count = conn.execute(
        '''
        SELECT COUNT(*)
        FROM contact_messages
        WHERE is_read = 0
        '''
    ).fetchone()[0]

    conn.close()
    return count

def init_db():
    conn = get_db_connection()
    # Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Employee',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Leave requests
    conn.execute('''
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            employee_name TEXT,
            leave_type TEXT,
            start_date DATE,
            end_date DATE,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    # Tasks
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT,
            status TEXT DEFAULT 'Todo',
            assigned_to TEXT,
            due_date DATE,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Meetings
    conn.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            meeting_date DATE,
            meeting_time TIME,
            description TEXT,
            participants TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Messages for chat
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER,
            username TEXT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (meeting_id) REFERENCES meetings (id)
        )
    ''')
    conn.commit()

    # Insert default users if none exist
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_pass = generate_password_hash('admin123')
        user_pass = generate_password_hash('user123')
        manager_pass = generate_password_hash('manager123')
        conn.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                     ('admin', admin_pass, 'admin@example.com', 'Admin'))
        conn.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                     ('user', user_pass, 'user@example.com', 'Employee'))
        conn.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                     ('manager', manager_pass, 'manager@example.com', 'Manager'))
        conn.commit()
    conn.close()

init_db()

@app.context_processor
def inject_unread_count():

    if session.get('role') == 'Admin':
        return {
            'unread_count': get_unread_message_count()
        }

    return {
        'unread_count': 0
    }

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        if session['role'] == 'Admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
       
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
       
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['email'] = user['email']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
           
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Admin Dashboard
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'Admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('index'))
       
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    total_users = len(users)
    admins = len([u for u in users if u['role'] == 'Admin'])
    managers = len([u for u in users if u['role'] == 'Manager'])
    employees = len([u for u in users if u['role'] == 'Employee'])
    
    leaves = conn.execute('SELECT * FROM leave_requests').fetchall()
    pending_leaves = len([l for l in leaves if l['status'] == 'Pending'])
    
    tasks = conn.execute('SELECT * FROM tasks').fetchall()
    total_tasks = len(tasks)
    
    meetings = conn.execute('SELECT * FROM meetings').fetchall()
    
    conn.close()
    return render_template('admin_dashboard.html', users=users, total_users=total_users, admins=admins, 
                         managers=managers, employees=employees, pending_leaves=pending_leaves, 
                         total_tasks=total_tasks, meetings=meetings)

# Admin User Management
@app.route('/admin/add', methods=['POST'])
def admin_add_user():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('index'))
       
    username = request.form['username']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])
    role = request.form['role']
   
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)',
                     (username, password, email, role))
        conn.commit()
        flash('User added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('Username already exists!', 'danger')
    finally:
        conn.close()
       
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit/<int:id>', methods=['POST'])
def admin_edit_user(id):
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('index'))
       
    username = request.form['username']
    email = request.form['email']
    role = request.form['role']
   
    conn = get_db_connection()
    conn.execute('UPDATE users SET username = ?, email = ?, role = ? WHERE id = ?', (username, email, role, id))
    conn.commit()
    conn.close()
    flash('User updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<int:id>')
def admin_delete_user(id):
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('index'))
       
    if id == session['user_id']:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin_dashboard'))
       
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/messages')
def admin_messages():

    if 'user_id' not in session or session['role'] != 'Admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()

    messages = conn.execute(
        '''
        SELECT *
        FROM contact_messages
        WHERE is_read = 0
        ORDER BY created_at DESC
        '''
    ).fetchall()

    conn.close()

    return render_template(
        'admin_messages.html',
        messages=messages
    )

@app.route('/admin/messages/read/<int:message_id>', methods=['POST'])
def admin_read_message(message_id):
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    conn = get_db_connection()
    conn.execute('UPDATE contact_messages SET is_read = 1 WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# User Dashboard
@app.route('/user')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
       
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # My leaves
    leaves = conn.execute('SELECT * FROM leave_requests WHERE user_id = ? ORDER BY created_at DESC', (session['user_id'],)).fetchall()
    
    # My tasks
    tasks = conn.execute('SELECT * FROM tasks WHERE assigned_to = ? ORDER BY due_date', (session['username'],)).fetchall()
    
    # Upcoming meetings
    meetings = conn.execute('SELECT * FROM meetings WHERE participants LIKE ? ORDER BY meeting_date', 
                          ('%' + session['username'] + '%',)).fetchall()
    
    conn.close()
    return render_template('user_dashboard.html', user=user, leaves=leaves, tasks=tasks, meetings=meetings)


@app.route('/user/update', methods=['POST'])
def user_update():
    if 'user_id' not in session:
        return redirect(url_for('login'))
       
    email = request.form['email']
    conn = get_db_connection()
    conn.execute('UPDATE users SET email = ? WHERE id = ?', (email, session['user_id']))
    conn.commit()
    conn.close()
    flash('Profile updated!', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/reset-password', methods=['POST'])
def user_reset_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
       
    hashed_password = generate_password_hash(request.form['password'])
    conn = get_db_connection()
    conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, session['user_id']))
    conn.commit()
    conn.close()
    flash('Password updated successfully!', 'success')
    return redirect(url_for('user_dashboard'))

# Leaves
@app.route('/leaves', methods=['GET', 'POST'])
def leaves():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    form = LeaveForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO leave_requests (user_id, employee_name, leave_type, start_date, end_date, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], session['username'], form.leave_type.data, form.start_date.data, 
              form.end_date.data, form.reason.data))
        conn.commit()
        conn.close()
        flash('Leave request submitted successfully!', 'success')
        return redirect(url_for('leaves'))
    
    conn = get_db_connection()
    leaves = conn.execute('SELECT * FROM leave_requests ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('leaves.html', form=form, leaves=leaves)

@app.route('/leaves/approve/<int:leave_id>')
def approve_leave(leave_id):
    if 'user_id' not in session or session['role'] != 'Admin':
        flash('Unauthorized!', 'danger')
        return redirect(url_for('leaves'))
    conn = get_db_connection()
    conn.execute("UPDATE leave_requests SET status = 'Approved' WHERE id = ?", (leave_id,))
    conn.commit()
    conn.close()
    flash('Leave approved!', 'success')
    return redirect(url_for('leaves'))

@app.route('/leaves/reject/<int:leave_id>')
def reject_leave(leave_id):
    if 'user_id' not in session or session['role'] != 'Admin':
        flash('Unauthorized!', 'danger')
        return redirect(url_for('leaves'))
    conn = get_db_connection()
    conn.execute("UPDATE leave_requests SET status = 'Rejected' WHERE id = ?", (leave_id,))
    conn.commit()
    conn.close()
    flash('Leave rejected!', 'info')
    return redirect(url_for('leaves'))

# Tasks
@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    form = TaskForm()
    if form.validate_on_submit() and session['role'] in ['Admin', 'Manager']:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO tasks (title, description, priority, assigned_to, due_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (form.title.data, form.description.data, form.priority.data, form.assigned_to.data, 
              form.due_date.data, session['username']))
        conn.commit()
        conn.close()
        flash('Task created!', 'success')
        return redirect(url_for('tasks'))
    
    conn = get_db_connection()
    tasks = conn.execute('SELECT * FROM tasks ORDER BY due_date').fetchall()
    users = conn.execute('SELECT username FROM users').fetchall()
    conn.close()
    return render_template('tasks.html', form=form, tasks=tasks, users=users)

@app.route('/tasks/update/<int:task_id>', methods=['POST'])
def update_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    status = request.form.get('status')
    conn = get_db_connection()
    conn.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, task_id))
    conn.commit()
    conn.close()
    flash('Task updated!', 'success')
    return redirect(url_for('tasks'))

@app.route('/tasks/delete/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session or session['role'] not in ['Admin', 'Manager']:
        flash('Unauthorized!', 'danger')
        return redirect(url_for('tasks'))
    conn = get_db_connection()
    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    flash('Task deleted!', 'success')
    return redirect(url_for('tasks'))

# Meetings
@app.route('/meetings', methods=['GET', 'POST'])
def meetings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    form = MeetingForm()
    if form.validate_on_submit():
        meeting_time_str = form.meeting_time.data.strftime('%H:%M:%S') if form.meeting_time.data else None
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO meetings (title, meeting_date, meeting_time, description, participants, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (form.title.data, form.meeting_date.data, meeting_time_str, 
              form.description.data, form.participants.data, session['username']))
        conn.commit()
        conn.close()
        flash('Meeting scheduled successfully!', 'success')
        return redirect(url_for('meetings'))
    
    # Handle Delete
    if request.method == 'POST' and 'delete_meeting' in request.form:
        meeting_id = request.form.get('delete_meeting')
        if session.get('role') == 'Admin':
            conn = get_db_connection()
            conn.execute('DELETE FROM meetings WHERE id = ?', (meeting_id,))
            conn.execute('DELETE FROM chat_messages WHERE meeting_id = ?', (meeting_id,))
            conn.commit()
            conn.close()
            flash('Meeting deleted successfully!', 'success')
            return redirect(url_for('meetings'))
    
    conn = get_db_connection()
    meetings_list = conn.execute('SELECT * FROM meetings ORDER BY meeting_date, meeting_time').fetchall()
    conn.close()
    return render_template('meetings.html', form=form, meetings=meetings_list)

@app.route('/meetings_room/<int:meeting_id>')
def meetings_room(meeting_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    meeting = conn.execute('SELECT * FROM meetings WHERE id = ?', (meeting_id,)).fetchone()
    messages = conn.execute('SELECT * FROM chat_messages WHERE meeting_id = ? ORDER BY timestamp', (meeting_id,)).fetchall()
    conn.close()
    
    if not meeting:
        flash('Meeting not found!', 'danger')
        return redirect(url_for('meetings'))
    
    # Check if user is participant
    participants = meeting['participants'].split(',')
    if session['username'] not in participants and session['role'] != 'Admin':
        flash('You are not authorized for this meeting!', 'danger')
        return redirect(url_for('meetings'))
    
    return render_template('meetings_room.html', meeting=meeting, messages=messages)

# SocketIO events
@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('status', {'msg': f"{session.get('username', 'User')} has joined the room."}, room=room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    emit('status', {'msg': f"{session.get('username', 'User')} has left the room."}, room=room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    message = data['message']
    username = session.get('username', 'Anonymous')
    
    conn = get_db_connection()
    conn.execute('INSERT INTO chat_messages (meeting_id, username, message) VALUES (?, ?, ?)',
                 (room, username, message))
    conn.commit()
    conn.close()
    
    emit('message', {'username': username, 'message': message, 'timestamp': datetime.now().strftime('%H:%M')}, room=room)

# Contact
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        # Save message to database so Admin can view it
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO contact_messages (name, email, subject, message, sender_role)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            form.name.data,
            form.email.data,
            form.subject.data,
            form.message.data,
            session.get('role', 'Guest')
        ))
        conn.commit()
        conn.close()

        # Send Email (existing functionality)
        msg = Message(
            subject=f"[Contact form] {form.subject.data}",
            recipients=['nadipallisudharshan@gmail.com'],
            reply_to=form.email.data
        )

        body_text = f"From: {form.name.data} - {form.email.data} \n\nMessage: \n{form.message.data}"

        file = form.attachment.data
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            file_size = os.path.getsize(file_path)

            if file_size > 20 * 1024 * 1024:
                body_text += f"\n\n[SYSTEM NOTE]: A larger file named `{filename}` was uploaded to server storage."
            else:
                with app.open_resource(file_path) as fp:
                    msg.attach(filename, file.mimetype, fp.read())
                body_text += f"\n\n[SYSTEM NOTE:] Attached file `{filename}` successfully"
        
        msg.body = body_text

        try:
            mail.send(msg)
            flash('Your message has been sent successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('contact.html', form=form)

@app.errorhandler(413)
def file_too_large(e):
    flash('File is too large! Maximum allowed size is 100MB', 'danger')
    return redirect(url_for('contact'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/home')
def home():
    return render_template('home.html')

# API for stats if needed
@app.route('/api/stats')
def api_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db_connection()
    # Add stats queries if needed
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("\n" + "═"*60)
    print(" 🚀 HrOne HR Management System STARTING...")
    print(" 👉 ADDRESS: http://127.0.0.1:5000")
    print("═"*60 + "\n")
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
