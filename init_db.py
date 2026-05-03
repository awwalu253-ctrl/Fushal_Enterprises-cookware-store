from app import create_app
from app.models_simple import db, User, Category, Product

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    print("✅ Database tables created successfully!")
    
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
        print("✅ Admin user created!")
    else:
        print("Admin user already exists!")
    
    # Create categories
    categories_data = [
        {'name': 'Knives', 'slug': 'knives', 'icon': 'knife', 'description': 'Professional kitchen knives', 'display_order': 1},
        {'name': 'Pans', 'slug': 'pans', 'icon': 'pan', 'description': 'Frying pans and skillets', 'display_order': 2},
        {'name': 'Pots', 'slug': 'pots', 'icon': 'pot', 'description': 'Cooking pots and dutch ovens', 'display_order': 3},
        {'name': 'Utensils', 'slug': 'utensils', 'icon': 'utensils', 'description': 'Cooking utensils and tools', 'display_order': 4},
    ]
    
    for cat_data in categories_data:
        existing = Category.query.filter_by(slug=cat_data['slug']).first()
        if not existing:
            cat = Category(**cat_data)
            db.session.add(cat)
    
    db.session.commit()
    print("✅ Categories created!")
    
    # Get category IDs
    knives = Category.query.filter_by(slug='knives').first()
    pans = Category.query.filter_by(slug='pans').first()
    pots = Category.query.filter_by(slug='pots').first()
    utensils = Category.query.filter_by(slug='utensils').first()
    
    # Create products
    products_data = [
        {
            'name': 'Professional Chef Knife',
            'slug': 'professional-chef-knife',
            'description': 'High-carbon stainless steel chef knife with ergonomic handle. Perfect for all your cutting needs.',
            'short_description': 'Premium 8-inch chef knife',
            'price': 89.99,
            'compare_price': 129.99,
            'sku': 'KNIFE-001',
            'stock_quantity': 50,
            'image_url': 'https://via.placeholder.com/400x400/E67E22/white?text=Chef+Knife',
            'category_id': knives.id if knives else None,
            'brand': 'Golden Kitchen',
            'is_featured': True,
            'is_bestseller': True,
            'is_new': False
        },
        {
            'name': 'Non-Stick Frying Pan',
            'slug': 'non-stick-frying-pan',
            'description': 'Durable non-stick coating, even heat distribution, easy to clean.',
            'short_description': '10-inch non-stick frying pan',
            'price': 49.99,
            'compare_price': 79.99,
            'sku': 'PAN-001',
            'stock_quantity': 100,
            'image_url': 'https://via.placeholder.com/400x400/F39C12/white?text=Frying+Pan',
            'category_id': pans.id if pans else None,
            'brand': 'Golden Kitchen',
            'is_featured': True,
            'is_bestseller': False,
            'is_new': True
        },
        {
            'name': 'Stainless Steel Saucepan',
            'slug': 'stainless-steel-saucepan',
            'description': 'Professional grade stainless steel saucepan with lid.',
            'short_description': '2-quart saucepan',
            'price': 39.99,
            'compare_price': 59.99,
            'sku': 'POT-001',
            'stock_quantity': 75,
            'image_url': 'https://via.placeholder.com/400x400/D35400/white?text=Saucepan',
            'category_id': pots.id if pots else None,
            'brand': 'Golden Kitchen',
            'is_featured': False,
            'is_bestseller': True,
            'is_new': False
        },
        {
            'name': 'Silicone Spatula Set',
            'slug': 'silicone-spatula-set',
            'description': 'Heat-resistant silicone spatula set, perfect for non-stick cookware.',
            'short_description': '3-piece spatula set',
            'price': 19.99,
            'compare_price': 29.99,
            'sku': 'UTL-001',
            'stock_quantity': 200,
            'image_url': 'https://via.placeholder.com/400x400/E67E22/white?text=Spatula',
            'category_id': utensils.id if utensils else None,
            'brand': 'Golden Kitchen',
            'is_featured': False,
            'is_bestseller': False,
            'is_new': True
        },
        {
            'name': 'Cast Iron Dutch Oven',
            'slug': 'cast-iron-dutch-oven',
            'description': '5.5 quart enameled cast iron dutch oven. Perfect for slow cooking and baking.',
            'short_description': '5.5qt Dutch oven',
            'price': 79.99,
            'compare_price': 129.99,
            'sku': 'POT-002',
            'stock_quantity': 30,
            'image_url': 'https://via.placeholder.com/400x400/F39C12/white?text=Dutch+Oven',
            'category_id': pots.id if pots else None,
            'brand': 'Golden Kitchen',
            'is_featured': True,
            'is_bestseller': False,
            'is_new': True
        },
    ]
    
    for prod_data in products_data:
        existing = Product.query.filter_by(sku=prod_data['sku']).first()
        if not existing:
            product = Product(**prod_data)
            db.session.add(product)
    
    db.session.commit()
    print(f"✅ Created {len(products_data)} products!")
    
    print("\n" + "="*50)
    print("🎉 Database setup complete!")
    print("="*50)
    print("\n📧 Admin Login:")
    print("   Email: admin@example.com")
    print("   Password: admin123")
    print("\n🌐 Run the app:")
    print("   python run.py")
    print("="*50)