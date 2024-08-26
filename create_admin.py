from app import app, db, Client
from werkzeug.security import generate_password_hash

def create_admin():
    # Set up the application context
    with app.app_context():
        # Check if the admin already exists
        admin = Client.query.filter_by(email='a@a.com').first()
        if not admin:
            # Create a new admin user
            hashed_password = generate_password_hash('admin')
            new_admin = Client(
                name='admin',
                email='a@a.com',
                password_hash=hashed_password,
                permis_type='A',  # Adjust as needed
                is_admin=True
            )
            db.session.add(new_admin)
            db.session.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")

if __name__ == '__main__':
    create_admin()
