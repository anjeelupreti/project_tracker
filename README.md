# Project Tracker

A comprehensive Django-based project management system with user role management, task tracking, and administrative controls.

## Features

- **User Authentication & Onboarding**
  - Email verification using django-allauth
  - Role-based access control (Admin, Team Lead, Member)
  - Designation request system with approval workflow

- **Project Management**
  - Create and manage departments
  - Assign team leads and members to projects
  - Track project progress and deadlines

- **Task Management**
  - Create, assign, and update tasks
  - Track task status and deadlines
  - Add comments and attachments to tasks

- **Dashboards**
  - Admin dashboard with comprehensive overview
  - Team lead dashboard for team management
  - Member dashboard for assigned tasks

- **Self-Service**
  - Profile management
  - Leave request system
  - Theme preferences (light/dark mode)

## Technology Stack

- **Backend**: Django 5.2
- **Frontend**: Bootstrap 5, Chart.js
- **Database**: SQLite (default), easily configurable for PostgreSQL/MySQL
- **Authentication**: django-allauth
- **History Tracking**: django-simple-history
- **Forms**: django-crispy-forms with Bootstrap 5

## Installation

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd ProjectTracker
   ```

2. **Create and activate virtual environment**:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Run migrations**:
   ```
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser**:
   ```
   python manage.py createsuperuser
   ```

6. **Run the development server**:
   ```
   python manage.py runserver
   ```

7. **Access the site**:
   - Visit `http://127.0.0.1:8000/` for the main site
   - Visit `http://127.0.0.1:8000/admin/` for the admin interface

## Initial Setup

1. Log in as the superuser you created
2. Create departments in the admin interface
3. Set up initial team leads and assign projects

## Usage

### For Admins

- Create and manage departments
- Create projects and assign team leads
- Approve designation requests
- Manage leave requests
- View comprehensive dashboards

### For Team Leads

- Manage team members
- Create and assign tasks
- Track team progress
- Review team member performance

### For Members

- View assigned tasks
- Update task status
- Request designations
- Request leave

## License

This project is licensed under the MIT License - see the LICENSE file for details. 