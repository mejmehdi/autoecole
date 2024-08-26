from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class Client(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    permis_type = db.Column(db.String(1), nullable=False)  # A, B, etc.
    is_admin = db.Column(db.Boolean, default=False)  # Admin flag
    lessons = db.relationship('Lesson', backref='client', lazy=True)
    tests = db.relationship('Test', back_populates='client', lazy=True)

    def get_id(self):
        return str(self.id)

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    question_1 = db.Column(db.String(255), nullable=False)
    correct_answer_1 = db.Column(db.String(255), nullable=False)
    false_answer_1 = db.Column(db.String(255), nullable=False)
    question_2 = db.Column(db.String(255), nullable=False)
    correct_answer_2 = db.Column(db.String(255), nullable=False)
    false_answer_2 = db.Column(db.String(255), nullable=False)
    question_3 = db.Column(db.String(255), nullable=False)
    correct_answer_3 = db.Column(db.String(255), nullable=False)
    false_answer_3 = db.Column(db.String(255), nullable=False)
    # Same for question 2 and question 3
    answer_1 = db.Column(db.String(255), nullable=True)  # Client's selected answer
    passed = db.Column(db.Boolean, default=False)
    reviewed = db.Column(db.Boolean, default=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship('Client', back_populates='tests')


with app.app_context():
    db.create_all()

# Load user function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return Client.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        return f"Thank you, {name}. Your message has been received."
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        client = Client.query.filter_by(email=email).first()

        if client and check_password_hash(client.password_hash, password):
            login_user(client)
            if client.is_admin:
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('client_dashboard'))
        
        flash("Invalid email or password.")
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/client', methods=['GET', 'POST'])
def client_dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    client = Client.query.get_or_404(current_user.id)
    
    if request.method == 'POST':
        question_1 = request.form.get('question_1')
        question_2 = request.form.get('question_2')
        question_3 = request.form.get('question_3')
        date = request.form.get('date')
        passed = request.form.get('passed') == 'on'

        if not date:
            flash("Date is required!", "error")
            return redirect(url_for('client_dashboard'))
        
        try:
            test_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format! Use YYYY-MM-DD.", "error")
            return redirect(url_for('client_dashboard'))

        new_test = Test(question_1=question_1, question_2=question_2, question_3=question_3, date=test_date, passed=passed, client_id=client.id)
        db.session.add(new_test)
        db.session.commit()
        return redirect(url_for('client_dashboard'))
    
    return render_template('client_dashboard.html', client=client)

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for('login'))
    
    clients = Client.query.all()
    return render_template('admin.html', clients=clients)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_client():
    if not current_user.is_admin:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        permis_type = request.form.get('permis_type')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == 'on'

        if not name or not email or not permis_type or not password:
            flash("All fields are required, including the password.")
            return redirect(request.url)

        hashed_password = generate_password_hash(password)
        new_client = Client(name=name, email=email, permis_type=permis_type, is_admin=is_admin, password_hash=hashed_password)
        db.session.add(new_client)
        db.session.commit()

        flash(f"Client {name} added successfully!")
        return redirect(url_for('admin'))

    return render_template('add_client.html')

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_client(id):
    if not current_user.is_admin:
        return redirect(url_for('login'))
    
    client = Client.query.get_or_404(id)
    if request.method == 'POST':
        client.name = request.form.get('name')
        client.email = request.form.get('email')
        client.permis_type = request.form.get('permis_type')
        client.is_admin = request.form.get('is_admin') == 'on'
        
        if request.form.get('password'):
            client.password_hash = generate_password_hash(request.form.get('password'))
        
        db.session.commit()
        flash(f"Client {client.name} updated successfully!")
        return redirect(url_for('admin'))
    
    return render_template('edit_client.html', client=client)

@app.route('/admin/delete/<int:id>', methods=['POST'])
@login_required
def delete_client(id):
    if not current_user.is_admin:
        return redirect(url_for('login'))
    
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    flash(f"Client {client.name} deleted successfully!")
    return redirect(url_for('admin'))

@app.route('/admin/client/<int:client_id>')
@login_required
def client_detail(client_id):
    if not current_user.is_admin:
        return redirect(url_for('login'))
    
    client = Client.query.get_or_404(client_id)
    return render_template('client_detail.html', client=client)

@app.route('/admin/client/<int:client_id>/add_lesson', methods=['GET', 'POST'])
@login_required
def add_lesson(client_id):
    if not current_user.is_admin:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        description = request.form.get('description')
        date = request.form.get('date')
        
        if not date:
            flash("Date is required!", "error")
            return redirect(url_for('add_lesson', client_id=client_id))

        try:
            lesson_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format! Use YYYY-MM-DD.", "error")
            return redirect(url_for('add_lesson', client_id=client_id))

        new_lesson = Lesson(description=description, date=lesson_date, client_id=client_id)
        db.session.add(new_lesson)
        db.session.commit()
        flash(f"Lesson added successfully!")
        return redirect(url_for('client_detail', client_id=client_id))
    
    return render_template('add_lesson.html', client_id=client_id)

@app.route('/admin/client/<int:client_id>/delete_lesson/<int:lesson_id>', methods=['POST'])
@login_required
def delete_lesson(client_id, lesson_id):
    if not current_user.is_admin:
        return redirect(url_for('login'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    db.session.delete(lesson)
    db.session.commit()
    flash(f"Lesson deleted successfully!")
    return redirect(url_for('client_detail', client_id=client_id))

@app.route('/admin/client/<int:client_id>/add_test', methods=['GET', 'POST'])
@login_required
def add_test(client_id):
    if not current_user.is_admin:
        return redirect(url_for('login'))

    client = Client.query.get_or_404(client_id)

    if request.method == 'POST':
        # Get the test data from the form
        date = request.form.get('date')
        question_1 = request.form.get('question_1')
        correct_answer_1 = request.form.get('correct_answer_1')
        false_answer_1 = request.form.get('false_answer_1')

        question_2 = request.form.get('question_2')
        correct_answer_2 = request.form.get('correct_answer_2')
        false_answer_2 = request.form.get('false_answer_2')

        question_3 = request.form.get('question_3')
        correct_answer_3 = request.form.get('correct_answer_3')
        false_answer_3 = request.form.get('false_answer_3')

        # Validate the form data
        if not date:
            flash("Date is required!", "error")
            return redirect(url_for('add_test', client_id=client_id))

        try:
            test_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format! Use YYYY-MM-DD.", "error")
            return redirect(url_for('add_test', client_id=client_id))

        # Create a new Test instance
        test = Test(
            date=test_date,
            question_1=question_1,
            correct_answer_1=correct_answer_1,
            false_answer_1=false_answer_1,
            question_2=question_2,
            correct_answer_2=correct_answer_2,
            false_answer_2=false_answer_2,
            question_3=question_3,
            correct_answer_3=correct_answer_3,
            false_answer_3=false_answer_3,
            client_id=client_id
        )

        # Add the test to the database
        db.session.add(test)
        db.session.commit()

        flash("Test added successfully!")
        return redirect(url_for('client_detail', client_id=client_id))

    return render_template('add_test.html', client_id=client_id)

@app.route('/client/<int:client_id>/take_test', methods=['GET', 'POST'])
@login_required
def take_test(client_id):
    client = Client.query.get_or_404(client_id)

    if request.method == 'POST':
        # Fetch the answers from the form
        answer_1 = request.form.get('answer_1')
        answer_2 = request.form.get('answer_2')
        answer_3 = request.form.get('answer_3')
        
        # Find the test that's being taken (assumes one test per client for simplicity)
        test = Test.query.filter_by(client_id=client_id).order_by(Test.date.desc()).first()
        
        # Save the answers to the test
        if test:
            test.answer_1 = answer_1
            test.answer_2 = answer_2
            test.answer_3 = answer_3
            test.reviewed = False  # The test needs to be reviewed by admin
            db.session.commit()
            flash("Test submitted successfully!")
            return redirect(url_for('client_dashboard'))
        
        flash("No test found to take!")
        return redirect(url_for('client_dashboard'))
    
    # Render the test form
    test = Test.query.filter_by(client_id=client_id).order_by(Test.date.desc()).first()
    
    return render_template('take_test.html', client=client, test=test)


@app.route('/admin/review_test/<int:test_id>', methods=['GET', 'POST'])
@login_required
def review_test(test_id):
    if not current_user.is_admin:
        return redirect(url_for('login'))

    test = Test.query.get_or_404(test_id)
    
    if request.method == 'POST':
        # Check if the admin marks the test as passed
        test.passed = request.form.get('passed') == 'on'
        test.reviewed = True
        db.session.commit()
        flash("Test reviewed successfully!")
        return redirect(url_for('admin'))

    return render_template('review_test.html', test=test)

@app.route('/admin/client/<int:client_id>/delete_test/<int:test_id>', methods=['POST'])
@login_required
def delete_test(client_id, test_id):
    if not current_user.is_admin:
        return redirect(url_for('login'))
    
    test = Test.query.get_or_404(test_id)
    db.session.delete(test)
    db.session.commit()
    flash("Test deleted successfully!")
    return redirect(url_for('client_detail', client_id=client_id))

if __name__ == '__main__':
    app.run(debug=True)
