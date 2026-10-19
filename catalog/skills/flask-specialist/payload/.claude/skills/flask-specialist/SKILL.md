---
name: flask-specialist
description: Build Python web applications with Flask, using the application factory pattern, Blueprints, and Flask-SQLAlchemy. Covers project structure, authentication, and configuration management. Use when creating Flask projects, organizing with Blueprints, implementing authentication, or troubleshooting circular imports, application context errors, or Blueprint registration.
metadata: 
  role: specialist

---

# Flask Skill

Production-tested patterns for Flask with the application factory pattern, Blueprints, and Flask-SQLAlchemy.

Latest Versions (Verified December 2025):

- Flask: 3.1.2
- Flask-SQLAlchemy: 3.1.1
- Flask-Login: 0.6.3
- Flask-WTF: 1.2.2
- Werkzeug: 3.1.3

## When to Use This Skill
- Creating a new Flask project.
- Organizing an application with Blueprints.
- Implementing login, registration, and protected routes.
- Integrating Flask-SQLAlchemy.
- Managing configuration for development, testing, and production.
- Building JSON API endpoints.
- Troubleshooting circular imports, application context errors, and Blueprint registration.
- Preparing a Flask application for testing and deployment.

## Quick Start

## Project Setup with uv

````bash
# Create project
uv init my-flask-app
cd my-flask-app

# Add dependencies
uv add flask flask-sqlalchemy flask-login flask-wtf python-dotenv

# Run development server
uv run flask --app app run --debug
````

## Minimal Working Example

```python
# app.py
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return {"message": "Hello, World!"}

if __name__ == "__main__":
    app.run(debug=True)

# Run: uv run flask --app app run --debug
  
```

## Project Structure: Application Factory

For maintainable applications, use the factory pattern with Blueprints.

my-flask-app/
├── pyproject.toml
├── config.py
├── run.py
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models.py
│   ├── main/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── main/
│   │   └── auth/
│   └── static/
│       ├── css/
│       └── js/
└── tests/
    ├── conftest.py
    └── test_main.py

## Core Patterns
### Application Factory

```python

# app/__init__.py

from flask import Flask
from app.extensions import db, login_manager
from config import Config

def create_app(config_class=Config):
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.main import bp as main_bp
    from app.auth import bp as auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Create database tables
    with app.app_context():
      db.create_all()

    return app
```


Create or update database schemas through migrations. For simple development or testing environments, db.create_all() can be used inside an application context after all models have been imported.

#### Key benefits:

- Supports multiple application instances with different configurations.
- Simplifies testing.
- Avoids global application dependencies and many circular imports.
- Allows extensions to be initialized independently of application creation.

## Extensions Module

```python
# app/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
```

Why use a separate file?

It prevents circular imports by allowing models, routes, and other modules to import extensions without importing the application instance.

## Configuration
```python
# config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///app.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"

```
Do not use a hardcoded fallback secret in production. Validate that SECRET_KEY is configured before starting a production application.

## Entry Point

```python
# run.py

from app import create_app
app = create_app()

if __name__ == "__main__":
    app.run()

# Run: uv run flask --app run run --debug
```

## Blueprints

### Creating a Blueprint

```python
# app/main/__init__.py

from flask import Blueprint

bp = Blueprint("main", __name__)

from app.main import routes # Import routes after creating the Blueprint.
```
```python
#app/main/routes.py

from flask import jsonify, render_template
from app.main import bp

@bp.route("/")
def index():
    return render_template("main/index.html")


@bp.route("/api/health")
def health():
    return jsonify({"status": "ok"})
```

## Blueprint with Templates and Static Files

Blueprint-specific template and static directories are useful when a feature needs to keep its own resources together.

```python
# app/auth/__init__.py

from flask import Blueprint

bp = Blueprint(
    "auth",
    __name__,
    template_folder="templates",
    static_folder="static",
)

from app.auth import routes
```

## Database Models
```python
# app/models.py

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """User model for authentication."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
```

## Database Guidelines
- Use constraints and indexes where appropriate.
- Never store plaintext passwords.
- Use Werkzeug's password-hashing utilities.
- Use migrations for schema changes.
- Keep database operations inside an application or request context.
- Prefer db.session.get() for primary-key lookups.
- Handle transaction failures and roll back failed sessions when necessary.

## Authentication with Flask-Login
### Authentication Forms

```python
#app/auth/forms.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    ValidationError,
)

from app.models import User


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()],
    )
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


class RegistrationForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8)],
    )
    confirm = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo(
                "password",
                message="Passwords must match",
            ),
        ],
    )
    submit = SubmitField("Register")

    def validate_email(self, field):
        existing_user = User.query.filter_by(
            email=field.data
        ).first()

        if existing_user:
            raise ValidationError("Email already registered.")
```

### Authentication Routes

```python
# app/auth/routes.py

from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)

from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.extensions import db
from app.models import User


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(
            email=form.email.data
        ).first()

        if user and user.is_active and user.check_password(
            form.password.data
        ):
            login_user(user, remember=form.remember.data)

            next_page = request.args.get("next")
            # Validate next_page before redirecting to prevent
            # open redirects to untrusted external destinations.

            flash("Logged in successfully!", "success")
            return redirect(next_page or url_for("main.index"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))

```

Validate the next parameter before using it as a redirect destination. For example, allow only local paths or explicitly trusted hosts.

Use POST for logout and keep CSRF protection enabled.

### Protecting Routes
Use @login_required for routes that require authentication, and perform authorization checks separately when access depends on roles or ownership.

```python
from flask import render_template
from flask_login import login_required, current_user

from app.main import bp

@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "main/dashboard.html",
        user=current_user,
    )
```

## API Routes: JSON

For REST APIs that do not use HTML templates, create a separate Blueprint.

```python
#app/api/__init__.py

from flask import Blueprint

bp = Blueprint("api", __name__)

from app.api import routes
```
In production, protect account creation with suitable authorization, rate limiting, validation, and abuse prevention. For cookie-authenticated APIs, retain appropriate CSRF protections.
```python
# app/api/routes.py

from flask import jsonify, request
from flask_login import login_required

from app.api import bp
from app.extensions import db
from app.models import User

@bp.route("/users", methods=["GET"])
@login_required
def get_users():
    users = User.query.all()

    return jsonify([
        {"id": user.id, "email": user.email}
        for user in users
    ])

@bp.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify({"error": "Expected a JSON object"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409

    user = User(email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "id": user.id,
        "email": user.email,
    }), 201
```

Register the API Blueprint with a prefix inside `create_app()`:

```python
# app/__init__.py (inside create_app)
from app.api import bp as api_bp

app.register_blueprint(api_bp, url_prefix="/api/v1")
```

## Critical Rules
### Always Do
- Use the application factory pattern.
- Put extension instances in a separate module.
- Import Blueprint routes after the Blueprint is created.
- Use current_app instead of importing a global application instance inside request-aware code.
- Use with app.app_context() when accessing context-dependent resources outside requests.
- Store secrets in environment variables or a dedicated secret manager.
- Keep CSRF protection enabled for browser forms.
- Use a production WSGI server such as Gunicorn.
- Use migrations to manage production database schemas.
- Validate and authorize user input on the server.

### Never Do
- Never import the application instance into models.
- Never access context-dependent database functionality without an application context.
- Never commit secrets to source control.
- Never enable Flask debug mode in production.
- Never use app.run() as the production server.
- Never disable CSRF protection globally as a workaround.
- Never trust arbitrary redirect URLs.
- Never expose sensitive user information in API responses.

## Common Errors and Fixes
### Circular Import Error

Error:
ImportError: cannot import name 'X' from partially initialized module

Cause: Modules import each other during initialization, such as the application importing models while models import the application.

Fix: Use extensions.py pattern.

Wrong approach:
```python
# app/__init__.py
from app.models import User # models.py imports db from here

# If app.models also imports objects from app, this can create a circular dependency.
```

Recommended approach:

```python
# app/extensions.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# app/__init__.py
from flask import Flask
from app.extensions import db

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    # Import models after extension setup when needed.
    from app import models

    return app

# Models import db from app.extensions, not the application instance.

```
### Working Outside Application Context

Error: RuntimeError: Working outside of application context

Cause: Accessing current_app, g, or context-dependent database functionality outside an active context.

# Wrong approach:

```python
from app import create_app
from app.models import User

app = create_app()
users = User.query.all()
```

Correct approach:

```python
from app import create_app
from app.models import User

app = create_app()

with app.app_context():
    users = User.query.all()
```

### Blueprint Not Found

Error: werkzeug.routing.BuildError: Could not build url for endpoint

Cause: Using the wrong endpoint name in url_for() or failing to register the Blueprint.

Wrong:
```python 
url_for("login")
```

Correct: Check that the Blueprint name is auth and that its routes are registered.

```python
url_for("auth.login")
```

### CSRF Token Missing

Error: A form submission fails because the CSRF token is missing or invalid.

Cause: A POST form does not include the token or the session is no longer valid.

Correct template:
For manually constructed Flask-WTF forms, include the generated CSRF field. Do not disable CSRF protection as a production workaround.
```html
<form method="post">
    {{ form.hidden_tag() }} <!-- Adds CSRF token -->

    <!-- Render form fields here -->

    <button type="submit">Submit</button>
</form>
```

## Testing

### Test Fixtures

```python
# tests/conftest.py

import pytest

from app import create_app
from app.extensions import db
from config import TestingConfig


@pytest.fixture
def app():
    app = create_app(TestingConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
``` 

Example Tests
```python
# tests/test_main.py

def test_index(client):
    response = client.get("/")
    assert response.status_code == 200


def test_register(client):
    response = client.post(
        "/auth/register",
        data={
            "email": "test@example.com",
            "password": "testpass123",
            "confirm": "testpass123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
```

Run the tests: uv run pytest

Ensure test configuration, CSRF behavior, database setup, and template rendering are consistent with the application. Add tests for failed authentication, duplicate accounts, invalid input, access control, and API error responses.

## Deployment
### Development
```bash 
uv run flask --app run run --debug
```

### Production with Gunicorn

Install Gunicorn: uv add gunicorn
Run: uv run gunicorn -w 4 -b 0.0.0.0:8000 "run:app"

Use a worker count appropriate for the deployment environment. Configure the reverse proxy, timeouts, logging, and health checks according to operational requirements.

## Docker

For production, consider a non-root user, a .dockerignore file, dependency lock files, image scanning, and a controlled database migration step.
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install uv && uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "run:app"]
```

# Environment Variables

Example .env file for local development:

SECRET_KEY=replace-with-a-local-development-secret
DATABASE_URL=sqlite:///app.db

For production, supply secrets through the deployment platform or a secret manager. Never commit a real .env file to source control.

### References
- Flask Documentation
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- The Flask Mega-Tutorial
- Application Factory Pattern: Flask Application Factories
