# HrOne - HR Management System

HrOne is a comprehensive HR Management System built using **Flask**, **SQLite**, and **Flask-SocketIO** for real-time interaction. It helps organizations streamline leaves tracking, tasks management, meeting coordination, and internal communications.

---

## 📁 Project Structure

Here is an overview of the project structure:

```text
HrOne/
├── cabin/                  # Python virtual environment (venv)
├── templates/              # HTML templates for rendering the UI
│   ├── base.html           # Base layout containing header/navbar and footer
│   ├── about.html          # About page
│   ├── admin_dashboard.html# Dashboard for admin (User Management & Stats overview)
│   ├── admin_messages.html # Admin view for messages received via the contact form
│   ├── contact.html        # Contact/feedback submission page with file attachments
│   ├── home.html           # Home landing page template
│   ├── leaves.html         # Leave requests submission and tracking
│   ├── login.html          # Authentication page
│   ├── meetings.html       # Meetings creation and list page
│   ├── meetings_room.html  # Live SocketIO-based group chat/meeting room
│   ├── tasks.html          # Tasks creation and status update page
│   └── user_dashboard.html # Employee/Manager dashboard
├── uploads/                # Directory where contact form attachments are stored
├── app.py                  # Main Flask application containing routes, SocketIO events & configuration
├── database.db             # SQLite database file containing project data
├── init_db.py              # Script to initialize database tables and insert demo users
├── requirements.txt        # Python package dependencies
└── README.md               # Project documentation (this file)
```

---

## 🚀 Getting Started & Commands

To get the application up and running locally, follow these steps:

### 1. Set Up the Virtual Environment
Create a virtual environment named `cabin` and activate it:

**Command Prompt / Windows PowerShell:**
```powershell
# Create the virtual environment
python -m venv cabin

# Activate the virtual environment
.\cabin\Scripts\activate
```

**Git Bash / Linux / macOS:**
```bash
# Create the virtual environment
python3 -m venv cabin

# Activate the virtual environment
source cabin/bin/activate
```

---

### 2. Install Dependencies
Install all the required Python packages:

```bash
pip install -r requirements.txt
```

---

### 3. Initialize the Database
Before running the application, initialize the SQLite database to create the necessary tables and populate them with the default users:

```bash
python init_db.py
```

Upon successful run, the following demo users will be created:
* **Admin Role:**
  * **Username:** `admin`
  * **Password:** `admin123`
* **Employee Role:**
  * **Username:** `user`
  * **Password:** `user123`
* **Manager Role:**
  * **Username:** `manager`
  * **Password:** `manager123`

---

### 4. Run the Application
Start the Flask application using the following command:

```bash
python app.py
```

Once running, navigate to `http://127.0.0.1:5000` in your web browser.

---

## 🛠️ Main Tech Stack
* **Backend:** Python, Flask, Flask-WTF (forms), Flask-Mail (email notifications)
* **Real-time Chat:** Flask-SocketIO & Eventlet
* **Database:** SQLite3
* **Frontend:** Bootstrap 5, FontAwesome, Vanilla CSS
