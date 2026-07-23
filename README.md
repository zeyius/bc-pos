Description :

A modern web-based Point of Sale (POS) system built with Flask, SQLite, and a responsive UI.
Designed for cafés and small businesses requiring daily session control, reporting, and structured sales management.

📌 Overview
Coffee POS is a lightweight yet structured POS application that supports:
Secure authentication
Business-day session management
Sales tracking
Daily & Monthly reporting
CSV export
Session-based reset logic
Clean and modern UI
The system ensures no mixing of sales between business sessions, while maintaining accurate calendar-based monthly accounting.

🚀 Core Features

🔐 Authentication
Secure login system
SHA256 password hashing
Role-based user management
Separate credential system for Reopen Day

🛒 Sales Engine
Dynamic cart system
Real-time subtotal calculation
Receipt generation
UUID-based receipt numbers
User tracking per sale
Business-day tagging (business_day_id)

📅 Business Day Management
Close Day functionality
Reopen Day with separate credentials
Automatic midnight session reset
Dashboard resets per session
Sales locked after day closure

📊 Reporting System
Daily Report
Session-based sales breakdown
Item-level detail per receipt
Total revenue & transaction count
Monthly Overview
Displays months (e.g. 02-2026)
Shows total revenue per month
Click month to view day breakdown
Monthly Report
Calendar-based aggregation
Daily totals inside month
Monthly total summary
CSV export support

🏗 System Architecture
Backend
Python 3.x
Flask
SQLite
SHA256 Password Hashing (hashlib)
Frontend
HTML5
CSS3
Responsive layout
Vanilla JavaScript

🗄 Database Schema Tables
users
products
sales
sale_items
business_days

Business Logic Model
Each sale belongs to a business_day
Closing a day:
Marks business day as closed
Locks further sales
Reopening:
Unlocks date
Creates a new business-day session

📂 Project Structure
coffee-pos/
│
├── app.py
├── init_db.py
├── seed_menu.py
├── pos.db
│
├── templates/
│   ├── layout.html
│   ├── dashboard.html
│   ├── new_sale.html
│   ├── daily_report.html
│   ├── monthly_report.html
│   ├── monthly_overview.html
│   └── reopen_day.html
│
├── static/
│   ├── styles.css
│   └── pos.js
│
└── README.md

⚙️ Installation
1️⃣ Clone Repository
git clone <your-repo-url>
cd coffee-pos
2️⃣ Create Virtual Environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
3️⃣ Install Dependencies
pip install flask
4️⃣ Initialize Database
rm pos.db
python init_db.py
python seed_menu.py
5️⃣ Run Application
flask run
Visit:
http://127.0.0.1:5000

🔑 Default Credentials
POS Login
Username: admin
Password: admin123
Reopen Day Credentials
Username: reopen
Password: reopen123
⚠️ Change credentials before production deployment.

📥 Exporting Reports
Monthly reports can be exported as CSV:
monthly_report_YYYY-MM.csv
Includes:
Month title
Daily totals
Monthly total summary

🧠 Business Logic Summary
Action	Result
Close Day	Locks sales & closes business session
Reopen Day	Unlocks date & starts new session
Midnight	New calendar day → new session
Dashboard	Shows current business session only
Monthly Report	Calendar-based aggregation

🔒 Security Notes
Passwords are hashed using SHA256.
No plaintext password storage.
Session-based login required.
Separate credential layer for reopening business day.

📈 Future Improvements
PDF report export
Multi-user permission dashboard
Inventory tracking
Tax configuration
Product image uploads
Sales analytics charts
Cloud deployment support

👨‍💻 Author
Developed as a structured Flask-based POS system with session-aware reporting and business-day management.
