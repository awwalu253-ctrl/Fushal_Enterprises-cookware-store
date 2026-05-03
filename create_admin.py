from app import create_app, db
from app.models_simple import User

app = create_app()

with app.app_context():
    # Create tables if they don't exist
    db.create_all()
    
    # Check if admin exists
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            email='admin@example.com',
            username='admin',
            first_name='Admin',
            last_name='User',
            is_admin=True,
            is_active=True,
            email_verified=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("="*50)
        print("✅ Admin user created successfully!")
        print("📧 Email: admin@example.com")
        print("🔑 Password: admin123")
        print("="*50)
    else:
        print("Admin user already exists!")