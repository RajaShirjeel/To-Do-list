from flask import Flask, render_template, url_for, flash, request, redirect, abort
from flask_sqlalchemy  import SQLAlchemy
from flask_login import login_user, LoginManager, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
from datetime import datetime
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'
secret_key = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] =os.environ.get("DB_URI", "sqlite:///tasks.db")
db = SQLAlchemy()
db.init_app(app)

Login_manager = LoginManager()
Login_manager.init_app(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    tasks = db.relationship('Task', backref='user')
    completed_tasks = db.relationship('Completed_Tasks', backref='user')
    
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100), nullable=False)
    task_due = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

class Completed_Tasks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    completed_task_name = db.Column(db.String(100), nullable=False)
    completed_task_due = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)


with app.app_context():
    db.create_all()


@Login_manager.user_loader
def load_user(user_id):
    if user_id is None:
        return None
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None


def login_required(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if not current_user.is_authenticated:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_func


@app.route('/')
def home():
    user = current_user
    today = datetime.today()
    task_due = today.strftime("%Y-%m-%d")
    date = datetime.strptime(task_due, "%Y-%m-%d").date()
    return render_template("index.html", user=user, date=date)


@app.route('/add_task', methods=['POST', 'GET'])
@login_required
def add_task():
    if request.method == "POST":
        task_due_date= request.form.get('task_due_date')
        new_task = Task(
            task_name = request.form.get('task_name'),
            task_due = datetime.strptime(task_due_date, "%Y-%m-%d").date(),
            user_id = current_user.id
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('home'))

    return render_template('add-task.html')


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")
        result = db.session.execute(db.select(User).where(User.email==email))
        user = result.scalar()
        if user:
            if (check_password_hash(user.password, password)):
                login_user(user)
                return redirect(url_for("home"))
            else:
                flash("Incorrect Password")
        else:
            flash("No user exists")
    return render_template("login-form.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get('password')
        result = db.session.execute(db.select(User).where(User.email==email))
        user = result.scalar()
        if not user:
            new_user = User(
                name = request.form.get('username'),
                email = email,
                password = generate_password_hash(password, salt_length=10)
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('home'))
        else:
            flash('Email already exists')

    return render_template('signup-form.html')


@app.route('/logout_user')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/completed_tasks", methods=['POST'])
def task_completed():
    if request.method == 'POST':
        completed_tasks = request.form.getlist('completed')
        for task in completed_tasks:
            result = db.session.execute(db.select(Task).where(Task.id == int(task)))
            com_task = result.scalar()
            new_task = Completed_Tasks(
                completed_task_name = com_task.task_name,
                completed_task_due = com_task.task_due,
                user_id = current_user.id
            )
            db.session.add(new_task)
            db.session.commit()
            db.session.delete(com_task)
            db.session.commit()
    return redirect(url_for('home'))


@app.route('/view-completed_tasks')
@login_required
def view_completed_tasks():
    results = db.session.execute(db.select(Completed_Tasks).order_by(Completed_Tasks.id))
    tasks = results.scalars().all()
    return render_template("completed_tasks.html", user=current_user)

@app.route('/about_me')
def about_me():
    return render_template("about.html")

@app.route("/retrive_task", methods=['POST'])
@login_required
def retrive_task():
    if request.method == 'POST':
        task_id = request.form.get('task_id')
        result = db.session.execute(db.select(Completed_Tasks).where(Completed_Tasks.id == task_id))
        task = result.scalar()
        new_task = Task(
            task_name = task.completed_task_name,
            task_due = task.completed_task_due,
            user_id = current_user.id
        )
        db.session.add(new_task)
        db.session.commit()
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=False)