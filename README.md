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
  - Member dashboard for assigned tasks and upcoming deadlines

- **Self-Service**
  - Profile management
  - Leave request system with approval workflow
  - Theme preferences (light/dark mode)

## Technology Stack

- **Backend**: Django 5.2
- **Frontend**: Bootstrap 5, Chart.js
- **Database**: SQLite (default), easily configurable for PostgreSQL/MySQL
- **Authentication**: django-allauth
- **History Tracking**: django-simple-history
- **Forms**: django-crispy-forms with Bootstrap 5

## Demo Screenshots

![Dashboard](screenshots/dashboard.png)
*Member dashboard showing task overview and upcoming deadlines*

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

## Environment Configuration

The project uses python-decouple for environment variable management. Create a `.env` file in the root directory with the following variables:

```
SECRET_KEY=your_secret_key
DEBUG=True
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_password
EMAIL_USE_TLS=True
```

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

## Project Structure

The project is organized into several Django apps:

- **accounts**: User authentication and profile management
- **core**: Core functionality and landing pages
- **projects**: Project and task management
- **dashboard**: Dashboard views for different user roles

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Django and its community for the excellent web framework
- Bootstrap team for the responsive frontend components
- All contributors who have helped shape this project 