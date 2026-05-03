from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Product, Category, db
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page - ONLY ONE INDEX FUNCTION"""
    featured_products = Product.query.filter_by(is_featured=True, is_active=True).limit(8).all()
    bestsellers = Product.query.filter_by(is_bestseller=True, is_active=True).limit(8).all()
    new_arrivals = Product.query.filter_by(is_new=True, is_active=True).order_by(Product.created_at.desc()).limit(8).all()
    
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
    """All products page"""
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    sort_by = request.args.get('sort', 'newest')
    
    query = Product.query.filter_by(is_active=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if sort_by == 'price_low':
        query = query.order_by(Product.price)
    elif sort_by == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'popular':
        query = query.order_by(Product.sales_count.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    categories = Category.query.filter_by(is_active=True).all()
    
    return render_template('main/products.html',
                         products=pagination.items,
                         pagination=pagination,
                         categories=categories,
                         current_category=category_id,
                         sort_by=sort_by)

@main_bp.route('/product/<slug>')
def product_detail(slug):
    """Product detail page"""
    product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    product.views_count += 1
    db.session.commit()
    
    related = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.is_active == True
    ).limit(4).all()
    
    return render_template('main/product_detail.html', 
                         product=product, 
                         related_products=related)

@main_bp.route('/search')
def search():
    """Search page"""
    query = request.args.get('q', '')
    products = Product.query.filter(
        Product.name.ilike(f'%{query}%'),
        Product.is_active == True
    ).limit(20).all() if query else []
    
    return render_template('main/search_results.html', 
                         products=products, 
                         query=query)

@main_bp.route('/faq')
def faq():
    """FAQ page"""
    return render_template('main/faq.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    if request.method == 'POST':
        flash('Thank you for your message!', 'success')
        return redirect(url_for('main.contact'))
    return render_template('main/contact.html')

@main_bp.route('/privacy-policy')
def privacy_policy():
    return render_template('main/privacy_policy.html')

@main_bp.route('/terms-of-service')
def terms_of_service():
    return render_template('main/terms_of_service.html')

@main_bp.route('/newsletter/subscribe', methods=['POST'])
def subscribe_newsletter():
    """Newsletter subscription"""
    email = request.form.get('email')
    flash('Subscribed successfully!', 'success')
    return redirect(request.referrer or url_for('main.index'))