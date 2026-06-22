import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('database.db')
conn.executescript('''
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS leave_requests;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS meetings;
DROP TABLE IF EXISTS participants;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS chat_messages;
DROP TABLE IF EXISTS contact_messages;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Employee',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE leave_requests (
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
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT,
    status TEXT DEFAULT 'Todo',
    assigned_to TEXT,
    due_date DATE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    meeting_date DATE,
    meeting_time TIME,
    description TEXT,
    participants TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    username TEXT,
    message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings (id)
);

CREATE TABLE contact_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    sender_role TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

conn.execute("DELETE FROM users")
conn.execute('INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)', 
             ('admin', generate_password_hash('admin123'), 'admin@hrone.com', 'Admin'))
conn.execute('INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)', 
             ('user', generate_password_hash('user123'), 'user@hrone.com', 'Employee'))
conn.execute('INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)', 
             ('manager', generate_password_hash('manager123'), 'manager@hrone.com', 'Manager'))

conn.commit()
print("database.db initialized successfully!")
print("Demo users:")
print("- admin / admin123 (Admin)")
print("- user / user123 (Employee)")
print("- manager / manager123 (Manager)")
conn.close()
