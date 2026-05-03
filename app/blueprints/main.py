from flask import Blueprint, render_template, request, jsonify, session, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Product, Category, db
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page"""
    # Get featured products
    featured_products = Product.query.filter_by(is_featured=True, is_active=True).limit(8).all()
    
    # Get bestsellers
    bestsellers = Product.query.filter_by(is_bestseller=True, is_active=True).limit(8).all()
    
    # Get new arrivals
    new_arrivals = Product.query.filter_by(is_new=True, is_active=True).order_by(Product.created_at.desc()).limit(8).all()
    
    # Get categories with product counts
    categories = db.session.query(
        Category, func.count(Product.id).label('product_count')
    ).outerjoin(Product).filter(Category.is_active == True).group_by(Category.id).order_by(Category.display_order).all()
    
    return render_template('main/index.html',
                         featured_products=featured_products,
                         bestsellers=bestsellers,
                         new_arrivals=new_arrivals,
                         categories=categories)

@main_bp.route('/products')
def products():
    """All products page with filtering"""
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    sort_by = request.args.get('sort', 'newest')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    search = request.args.get('search', '')
    
    # Build query
    query = Product.query.filter_by(is_active=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%'),
                Product.brand.ilike(f'%{search}%')
            )
        )
    
    if min_price:
        query = query.filter(Product.price >= min_price)
    if max_price:
        query = query.filter(Product.price <= max_price)
    
    # Sorting
    if sort_by == 'price_low':
        query = query.order_by(Product.price)
    elif sort_by == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'popular':
        query = query.order_by(Product.sales_count.desc())
    elif sort_by == 'rating':
        query = query.order_by(Product.rating.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    
    # Pagination
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    products = pagination.items
    
    # Get all categories for filter
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    
    # Get price range for filter
    price_range = db.session.query(
        func.min(Product.price).label('min'),
        func.max(Product.price).label('max')
    ).filter_by(is_active=True).first()
    
    return render_template('main/products.html',
                         products=products,
                         pagination=pagination,
                         categories=categories,
                         current_category=category_id,
                         sort_by=sort_by,
                         min_price=min_price,
                         max_price=max_price,
                         price_range=price_range,
                         search=search)

@main_bp.route('/product/<slug>')
def product_detail(slug):
    """Product detail page"""
    product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    
    # Increment view count
    product.views_count += 1
    db.session.commit()
    
    # Get related products (same category)
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.is_active == True
    ).limit(4).all()
    
    return render_template('main/product_detail.html',
                         product=product,
                         related_products=related_products)

@main_bp.route('/search')
def search():
    """Search page with filters"""
    query = request.args.get('q', '')
    category_id = request.args.get('category', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    products_query = Product.query.filter(Product.is_active == True)
    
    if query:
        products_query = products_query.filter(
            db.or_(
                Product.name.ilike(f'%{query}%'),
                Product.description.ilike(f'%{query}%'),
                Product.brand.ilike(f'%{query}%')
            )
        )
    
    if category_id:
        products_query = products_query.filter_by(category_id=category_id)
    
    if min_price:
        products_query = products_query.filter(Product.price >= min_price)
    if max_price:
        products_query = products_query.filter(Product.price <= max_price)
    
    products = products_query.limit(50).all()
    categories = Category.query.filter_by(is_active=True).all()
    
    return render_template('main/search_results.html', 
                         products=products, 
                         query=query,
                         categories=categories)

@main_bp.route('/search/suggest')
def search_suggest():
    """Autocomplete suggestions API"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    # Search products by name, brand, or category
    products = Product.query.filter(
        db.or_(
            Product.name.ilike(f'%{query}%'),
            Product.brand.ilike(f'%{query}%')
        ),
        Product.is_active == True
    ).limit(10).all()
    
    # Also search categories
    categories = Category.query.filter(
        Category.name.ilike(f'%{query}%'),
        Category.is_active == True
    ).limit(5).all()
    
    suggestions = []
    
    # Add product suggestions
    for p in products:
        suggestions.append({
            'type': 'product',
            'name': p.name,
            'slug': p.slug,
            'price': p.price,
            'image': p.image_url,
            'url': url_for('main.product_detail', slug=p.slug)
        })
    
    # Add category suggestions
    for c in categories:
        suggestions.append({
            'type': 'category',
            'name': c.name,
            'slug': c.slug,
            'url': url_for('main.products', category=c.id)
        })
    
    return jsonify(suggestions[:10])  # Limit to 10 suggestions

@main_bp.route('/product/<int:product_id>/review', methods=['POST'])
@login_required
def add_review(product_id):
    """Add a product review"""
    from app.models import Review, OrderItem
    
    product = Product.query.get_or_404(product_id)
    
    rating = int(request.form.get('rating', 0))
    title = request.form.get('title')
    comment = request.form.get('comment')
    
    if rating < 1 or rating > 5:
        flash('Please provide a valid rating', 'danger')
        return redirect(url_for('main.product_detail', slug=product.slug))
    
    # Check if user has purchased this product
    has_purchased = OrderItem.query.join(Order).filter(
        Order.user_id == current_user.id,
        OrderItem.product_id == product_id,
        Order.status == 'delivered'
    ).first() is not None
    
    # Check if user already reviewed
    existing_review = Review.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if existing_review:
        flash('You have already reviewed this product', 'warning')
        return redirect(url_for('main.product_detail', slug=product.slug))
    
    review = Review(
        user_id=current_user.id,
        product_id=product_id,
        rating=rating,
        title=title,
        comment=comment,
        is_verified_purchase=has_purchased,
        is_approved=has_purchased  # Auto-approve for verified purchases
    )
    
    db.session.add(review)
    db.session.commit()
    
    # Update product rating
    all_reviews = Review.query.filter_by(product_id=product_id, is_approved=True).all()
    if all_reviews:
        avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
        product.rating = avg_rating
        product.rating_count = len(all_reviews)
        db.session.commit()
    
    flash('Thank you for your review! It will appear after moderation.', 'success')
    return redirect(url_for('main.product_detail', slug=product.slug))

@main_bp.route('/faq')
def faq():
    """FAQ page"""
    faq_categories = {
        'ordering': [
            {'question': 'How do I place an order?', 'answer': 'Simply browse our products, add items to your cart, and proceed to checkout.'},
            {'question': 'Can I modify my order after placing it?', 'answer': 'You can modify your order within 30 minutes of placing it. Contact our support team.'},
            {'question': 'What payment methods do you accept?', 'answer': 'We accept all major credit cards, PayPal, and Apple Pay.'}
        ],
        'shipping': [
            {'question': 'How long does shipping take?', 'answer': 'Standard shipping takes 3-5 business days. Express shipping takes 1-2 business days.'},
            {'question': 'Do you ship internationally?', 'answer': 'Yes, we ship worldwide. International delivery takes 7-14 business days.'},
            {'question': 'How can I track my order?', 'answer': 'You\'ll receive a tracking number via email once your order ships.'}
        ],
        'returns': [
            {'question': 'What is your return policy?', 'answer': 'We offer 30-day returns for unused items in original packaging.'},
            {'question': 'Who pays for return shipping?', 'answer': 'We provide free return shipping for defective items.'}
        ]
    }
    return render_template('main/faq.html', faq_categories=faq_categories)

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        flash('Thank you for your message. We\'ll get back to you soon!', 'success')
        return redirect(url_for('main.contact'))
    
    return render_template('main/contact.html')

@main_bp.route('/privacy-policy')
def privacy_policy():
    return render_template('main/privacy_policy.html')

@main_bp.route('/terms-of-service')
def terms_of_service():
    return render_template('main/terms_of_service.html')

@main_bp.route('/search/advanced')
def advanced_search():
    """Advanced search page"""
    categories = Category.query.filter_by(is_active=True).all()
    return render_template('main/advanced_search.html', categories=categories)

@main_bp.route('/wishlist')
@login_required
def wishlist():
    """Wishlist page"""
    from app.models import Wishlist
    items = Wishlist.query.filter_by(user_id=current_user.id).all()
    return render_template('main/wishlist.html', wishlist_items=items)

@main_bp.route('/newsletter/subscribe', methods=['POST'])
def subscribe_newsletter():
    """Newsletter subscription"""
    email = request.form.get('email')
    from app.models import NewsletterSubscriber
    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.unsubscribed_at = None
            db.session.commit()
            flash('Welcome back!', 'success')
        else:
            flash('Already subscribed!', 'info')
    else:
        subscriber = NewsletterSubscriber(email=email)
        db.session.add(subscriber)
        db.session.commit()
        flash('Subscribed successfully!', 'success')
    return redirect(request.referrer or url_for('main.index'))