from app import create_app
from app.models import db, User, Category, Product

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    print("✓ Database tables created")
    
    # Create admin user
    if not User.query.filter_by(email='admin@example.com').first():
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
        print("✓ Admin user created (admin@example.com / admin123)")
    
    # Create categories
    categories = [
        Category(name='Knives', slug='knives', icon='knife', display_order=1),
        Category(name='Pans', slug='pans', icon='pan', display_order=2),
        Category(name='Pots', slug='pots', icon='pot', display_order=3),
        Category(name='Utensils', slug='utensils', icon='utensils', display_order=4),
    ]
    
    for cat in categories:
        if not Category.query.filter_by(slug=cat.slug).first():
            db.session.add(cat)
    db.session.commit()
    print("✓ Categories created")
    
    # Get category IDs
    knives = Category.query.filter_by(slug='knives').first()
    pans = Category.query.filter_by(slug='pans').first()
    pots = Category.query.filter_by(slug='pots').first()
    utensils = Category.query.filter_by(slug='utensils').first()
    
    # Create products
    products = [
        Product(
            name='Professional Chef Knife',
            slug='professional-chef-knife',
            description='High-carbon stainless steel chef knife',
            short_description='Premium 8-inch chef knife',
            price=89.99,
            compare_price=129.99,
            sku='KNIFE-001',
            stock_quantity=50,
            image_url='https://via.placeholder.com/400x400/E67E22/white?text=Chef+Knife',
            category_id=knives.id,
            brand='Golden Kitchen',
            is_featured=True,
            is_bestseller=True
        ),
        Product(
            name='Non-Stick Frying Pan',
            slug='non-stick-frying-pan',
            description='Durable non-stick coating frying pan',
            short_description='10-inch frying pan',
            price=49.99,
            compare_price=79.99,
            sku='PAN-001',
            stock_quantity=100,
            image_url='https://via.placeholder.com/400x400/F39C12/white?text=Frying+Pan',
            category_id=pans.id,
            brand='Golden Kitchen',
            is_featured=True,
            is_new=True
        ),
        Product(
            name='Stainless Steel Saucepan',
            slug='stainless-steel-saucepan',
            description='Professional stainless steel saucepan',
            short_description='2-quart saucepan',
            price=39.99,
            compare_price=59.99,
            sku='POT-001',
            stock_quantity=75,
            image_url='https://via.placeholder.com/400x400/D35400/white?text=Saucepan',
            category_id=pots.id,
            brand='Golden Kitchen',
            is_bestseller=True
        ),
        Product(
            name='Silicone Spatula Set',
            slug='silicone-spatula-set',
            description='Heat-resistant silicone spatulas',
            short_description='3-piece spatula set',
            price=19.99,
            compare_price=29.99,
            sku='UTL-001',
            stock_quantity=200,
            image_url='https://via.placeholder.com/400x400/E67E22/white?text=Spatula',
            category_id=utensils.id,
            brand='Golden Kitchen',
            is_new=True
        ),
    ]
    
    for product in products:
        if not Product.query.filter_by(sku=product.sku).first():
            db.session.add(product)
    db.session.commit()
    print(f"✓ {len(products)} products created")
    
    print("\n" + "="*50)
    print("✅ SETUP COMPLETE!")
    print("="*50)
    print("\n🔐 Login credentials:")
    print("   Email: admin@example.com")
    print("   Password: admin123")
    print("\n🚀 Run the app:")
    print("   python run.py")
    print("="*50)