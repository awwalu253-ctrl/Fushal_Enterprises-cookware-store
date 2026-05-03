# This will run as part of the build process
from app import create_app, db
from app.models import User, Category, Product, Coupon

app = create_app()

with app.app_context():
    db.create_all()
    
    # Create admin user if not exists
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            email='admin@example.com',
            username='admin',
            first_name='Admin',
            is_admin=True,
            is_active=True,
            email_verified=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
    
    # Create categories
    categories = ['Knives', 'Pans', 'Pots', 'Utensils']
    for idx, cat_name in enumerate(categories):
        if not Category.query.filter_by(name=cat_name).first():
            cat = Category(
                name=cat_name,
                slug=cat_name.lower(),
                display_order=idx + 1,
                is_active=True
            )
            db.session.add(cat)
    
    # Create sample coupon
    if not Coupon.query.filter_by(code='WELCOME10').first():
        coupon = Coupon(
            code='WELCOME10',
            description='10% off your order',
            discount_type='percentage',
            discount_value=10,
            min_order_amount=1000,
            max_discount=5000,
            usage_limit=100,
            is_active=True
        )
        db.session.add(coupon)
    
    db.session.commit()
    print("Database initialized successfully!")