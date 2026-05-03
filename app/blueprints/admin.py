from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from app.models import User, Product, Category, Order, db
from app.models import Coupon, Review, OrderItem, NewsletterSubscriber
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func
import io
import csv

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated

# ==================== DASHBOARD ====================

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    # Today's sales
    today_sales = db.session.query(func.sum(Order.total)).filter(
        func.date(Order.created_at) == today,
        Order.status != 'cancelled'
    ).scalar() or 0
    
    yesterday_sales = db.session.query(func.sum(Order.total)).filter(
        func.date(Order.created_at) == yesterday,
        Order.status != 'cancelled'
    ).scalar() or 0
    
    daily_growth = 0
    if yesterday_sales and yesterday_sales > 0:
        daily_growth = round(((float(today_sales) - float(yesterday_sales)) / float(yesterday_sales)) * 100, 1)
    
    # Order statistics
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    
    # Customer statistics
    total_customers = User.query.filter_by(is_admin=False).count()
    month_start = datetime(today.year, today.month, 1)
    new_customers = User.query.filter(
        User.created_at >= month_start,
        User.is_admin == False
    ).count()
    
    # Product statistics
    total_products = Product.query.count()
    low_stock_products = Product.query.filter(
        Product.stock_quantity <= Product.low_stock_threshold,
        Product.stock_quantity > 0
    ).count()
    
    # Top products
    from app.models import OrderItem
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem).group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    
    top_products_list = []
    for p in top_products:
        top_products_list.append({
            'name': p.name,
            'total_sold': p.total_sold
        })
    
    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    # Chart data for last 7 days
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        daily_total = db.session.query(func.sum(Order.total)).filter(
            func.date(Order.created_at) == date,
            Order.status != 'cancelled'
        ).scalar() or 0
        chart_labels.append(date.strftime('%a'))
        chart_data.append(float(daily_total))
    
    # Pending reviews count for sidebar badge
    from app.models import Review
    pending_reviews_count = Review.query.filter_by(is_approved=False).count()
    
    return render_template('admin/dashboard.html',
                         today_sales=float(today_sales),
                         daily_growth=daily_growth,
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         total_customers=total_customers,
                         new_customers=new_customers,
                         total_products=total_products,
                         low_stock_products=low_stock_products,
                         top_products=top_products_list,
                         recent_orders=recent_orders,
                         chart_labels=chart_labels,
                         chart_data=chart_data,
                         pending_reviews_count=pending_reviews_count)

# ==================== API ENDPOINTS ====================

@admin_bp.route('/api/pending-orders-count')
@admin_required
def pending_orders_count():
    count = Order.query.filter_by(status='pending').count()
    return jsonify({'count': count})

@admin_bp.route('/api/pending-reviews-count')
@admin_required
def pending_reviews_count_api():
    from app.models import Review
    count = Review.query.filter_by(is_approved=False).count()
    return jsonify({'count': count})

@admin_bp.route('/api/sales-data')
@admin_required
def sales_data_api():
    days = request.args.get('days', 7, type=int)
    sales_by_day = []
    for i in range(days):
        date = datetime.utcnow().date() - timedelta(days=i)
        daily_total = db.session.query(func.sum(Order.total)).filter(
            func.date(Order.created_at) == date,
            Order.status != 'cancelled'
        ).scalar() or 0
        sales_by_day.append({
            'date': date.strftime('%Y-%m-%d'),
            'total': float(daily_total)
        })
    sales_by_day.reverse()
    return jsonify({
        'labels': [d['date'] for d in sales_by_day],
        'values': [d['total'] for d in sales_by_day]
    })

@admin_bp.route('/api/dashboard-stats')
@admin_required
def dashboard_stats_api():
    today = datetime.utcnow().date()
    today_sales = db.session.query(func.sum(Order.total)).filter(
        func.date(Order.created_at) == today,
        Order.status != 'cancelled'
    ).scalar() or 0
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    total_customers = User.query.filter_by(is_admin=False).count()
    total_products = Product.query.count()
    return jsonify({
        'today_sales': float(today_sales),
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_customers': total_customers,
        'total_products': total_products
    })

@admin_bp.route('/api/recent-orders')
@admin_required
def recent_orders_api():
    orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    return jsonify({
        'orders': [{
            'id': o.id,
            'order_number': o.order_number,
            'shipping_name': o.shipping_name,
            'created_at': o.created_at.strftime('%Y-%m-%d %H:%M') if o.created_at else 'N/A',
            'total': float(o.total),
            'status': o.status,
            'payment_status': o.payment_status
        } for o in orders]
    })

@admin_bp.route('/api/analytics-data')
@admin_required
def analytics_data_api():
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow().date() - timedelta(days=days)
    
    from app.models import OrderItem, Review
    
    revenue_data = db.session.query(
        func.date(Order.created_at).label('date'),
        func.sum(Order.total).label('revenue')
    ).filter(
        Order.created_at >= start_date,
        Order.status != 'cancelled'
    ).group_by(func.date(Order.created_at)).all()
    
    category_sales = db.session.query(
        Category.name,
        func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
    ).join(Product).join(OrderItem).join(Order).filter(
        Order.status != 'cancelled'
    ).group_by(Category.id).all()
    
    customer_growth = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date,
        User.is_admin == False
    ).group_by(func.date(User.created_at)).all()
    
    total_revenue = db.session.query(func.sum(Order.total)).filter(
        Order.status != 'cancelled'
    ).scalar() or 0
    avg_order_value = db.session.query(func.avg(Order.total)).filter(
        Order.status != 'cancelled'
    ).scalar() or 0
    total_orders = Order.query.filter(Order.status != 'cancelled').count()
    total_visitors = db.session.query(func.count(db.distinct(Order.user_id))).scalar() or 1
    conversion_rate = round((total_orders / total_visitors) * 100, 1)
    total_customers = User.query.filter_by(is_admin=False).count()
    repeat_customers = db.session.query(Order.user_id).group_by(Order.user_id).having(func.count(Order.id) > 1).count()
    repeat_rate = round((repeat_customers / total_customers) * 100, 1) if total_customers > 0 else 0
    
    return jsonify({
        'total_revenue': float(total_revenue),
        'avg_order_value': float(avg_order_value),
        'conversion_rate': conversion_rate,
        'repeat_rate': repeat_rate,
        'revenue_labels': [d.date.strftime('%Y-%m-%d') for d in revenue_data],
        'revenue_values': [float(d.revenue) for d in revenue_data],
        'category_labels': [c.name for c in category_sales],
        'category_values': [float(c.revenue) for c in category_sales],
        'customer_labels': [c.date.strftime('%Y-%m-%d') for c in customer_growth],
        'customer_values': [c.count for c in customer_growth]
    })

@admin_bp.route('/api/sales-report')
@admin_required
def sales_report_api():
    report_type = request.args.get('type', 'daily')
    
    if report_type == 'daily':
        data = []
        for i in range(29, -1, -1):
            date = datetime.utcnow().date() - timedelta(days=i)
            daily_sales = db.session.query(func.sum(Order.total)).filter(
                func.date(Order.created_at) == date,
                Order.status != 'cancelled'
            ).scalar() or 0
            order_count = Order.query.filter(
                func.date(Order.created_at) == date,
                Order.status != 'cancelled'
            ).count()
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'sales': float(daily_sales),
                'orders': order_count
            })
        return jsonify(data)
    elif report_type == 'monthly':
        data = []
        for i in range(11, -1, -1):
            month = datetime.utcnow().date().replace(day=1) - timedelta(days=30*i)
            month_start = month.replace(day=1)
            if month.month == 12:
                month_end = month.replace(year=month.year+1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month.replace(month=month.month+1, day=1) - timedelta(days=1)
            monthly_sales = db.session.query(func.sum(Order.total)).filter(
                Order.created_at >= month_start,
                Order.created_at <= month_end,
                Order.status != 'cancelled'
            ).scalar() or 0
            data.append({
                'month': month_start.strftime('%b %Y'),
                'sales': float(monthly_sales)
            })
        return jsonify(data)
    return jsonify([])

# ==================== ANALYTICS ====================

@admin_bp.route('/analytics')
@admin_required
def analytics():
    from app.models import OrderItem
    
    sales_by_day = db.session.query(
        func.date(Order.created_at).label('date'),
        func.sum(Order.total).label('sales')
    ).filter(Order.created_at >= datetime.utcnow() - timedelta(days=30)).group_by(func.date(Order.created_at)).all()
    
    sales_by_category = db.session.query(
        Category.name,
        func.sum(OrderItem.quantity * OrderItem.price).label('revenue')
    ).join(Product).join(OrderItem).group_by(Category.id).all()
    
    avg_order_value = db.session.query(func.avg(Order.total)).scalar() or 0
    total_orders = Order.query.count()
    total_visitors = db.session.query(func.count(db.distinct(Order.user_id))).scalar() or 1
    conversion_rate = (total_orders / total_visitors) * 100
    total_customers = User.query.filter_by(is_admin=False).count()
    repeat_customers = db.session.query(Order.user_id).group_by(Order.user_id).having(func.count(Order.id) > 1).count()
    repeat_rate = (repeat_customers / total_customers) * 100 if total_customers > 0 else 0
    
    return render_template('admin/analytics.html', 
                         sales_by_day=sales_by_day, 
                         sales_by_category=sales_by_category,
                         avg_order_value=avg_order_value, 
                         conversion_rate=conversion_rate,
                         repeat_rate=repeat_rate)

# ==================== PRODUCT MANAGEMENT ====================

@admin_bp.route('/products')
@admin_required
def manage_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        product = Product(
            name=request.form.get('name'),
            slug=request.form.get('name').lower().replace(' ', '-'),
            description=request.form.get('description'),
            short_description=request.form.get('short_description'),
            price=float(request.form.get('price')),
            compare_price=float(request.form.get('compare_price')) if request.form.get('compare_price') else None,
            sku=request.form.get('sku'),
            stock_quantity=int(request.form.get('stock_quantity', 0)),
            low_stock_threshold=int(request.form.get('low_stock_threshold', 5)),
            category_id=int(request.form.get('category_id')) if request.form.get('category_id') else None,
            brand=request.form.get('brand'),
            image_url=request.form.get('image_url'),
            is_featured='is_featured' in request.form,
            is_bestseller='is_bestseller' in request.form,
            is_new='is_new' in request.form
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin.manage_products'))
    
    categories = Category.query.all()
    return render_template('admin/add_product.html', categories=categories)

@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.slug = request.form.get('name').lower().replace(' ', '-')
        product.description = request.form.get('description')
        product.short_description = request.form.get('short_description')
        product.price = float(request.form.get('price'))
        product.compare_price = float(request.form.get('compare_price')) if request.form.get('compare_price') else None
        product.sku = request.form.get('sku')
        product.stock_quantity = int(request.form.get('stock_quantity', 0))
        product.low_stock_threshold = int(request.form.get('low_stock_threshold', 5))
        product.category_id = int(request.form.get('category_id')) if request.form.get('category_id') else None
        product.brand = request.form.get('brand')
        product.image_url = request.form.get('image_url')
        product.is_featured = 'is_featured' in request.form
        product.is_bestseller = 'is_bestseller' in request.form
        product.is_new = 'is_new' in request.form
        product.is_active = 'is_active' in request.form
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin.manage_products'))
    
    categories = Category.query.all()
    return render_template('admin/edit_product.html', product=product, categories=categories)

@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted', 'success')
    return redirect(url_for('admin.manage_products'))

@admin_bp.route('/products/export')
@admin_required
def export_products():
    products = Product.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'SKU', 'Price', 'Stock', 'Category', 'Brand'])
    for p in products:
        writer.writerow([p.id, p.name, p.sku, p.price, p.stock_quantity, p.category.name if p.category else '', p.brand])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name=f'products_{datetime.now().strftime("%Y%m%d")}.csv')

@admin_bp.route('/products/import', methods=['POST'])
@admin_required
def import_products():
    if 'csv_file' not in request.files:
        flash('No file uploaded', 'danger')
        return redirect(url_for('admin.manage_products'))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('admin.manage_products'))
    
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)
    next(csv_input)
    
    count = 0
    for row in csv_input:
        product = Product(
            name=row[0],
            sku=row[1],
            price=float(row[2]),
            stock_quantity=int(row[3]),
            description=row[4] if len(row) > 4 else '',
            is_active=True
        )
        db.session.add(product)
        count += 1
    
    db.session.commit()
    flash(f'Imported {count} products successfully!', 'success')
    return redirect(url_for('admin.manage_products'))

@admin_bp.route('/bulk-import')
@admin_required
def bulk_import():
    return render_template('admin/bulk_import.html')

# ==================== CATEGORY MANAGEMENT ====================

@admin_bp.route('/categories')
@admin_required
def manage_categories():
    categories = Category.query.order_by(Category.display_order).all()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/categories/add', methods=['POST'])
@admin_required
def add_category():
    category = Category(
        name=request.form.get('name'),
        slug=request.form.get('name').lower().replace(' ', '-'),
        description=request.form.get('description'),
        icon=request.form.get('icon'),
        display_order=int(request.form.get('display_order', 0))
    )
    db.session.add(category)
    db.session.commit()
    flash('Category added', 'success')
    return redirect(url_for('admin.manage_categories'))

# ==================== ORDER MANAGEMENT ====================

@admin_bp.route('/orders')
@admin_required
def manage_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@admin_bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = request.form.get('status')
    db.session.commit()
    flash(f'Order #{order.order_number} status updated', 'success')
    return redirect(url_for('admin.manage_orders'))

# ==================== CUSTOMER MANAGEMENT ====================

@admin_bp.route('/customers')
@admin_required
def manage_customers():
    customers = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).all()
    return render_template('admin/customers.html', customers=customers)

@admin_bp.route('/customers/<int:user_id>/verify', methods=['POST'])
@admin_required
def verify_customer(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = True
    user.email_verified = True
    db.session.commit()
    flash('Customer verified', 'success')
    return redirect(url_for('admin.manage_customers'))

@admin_bp.route('/customers/export')
@admin_required
def export_customers():
    customers = User.query.filter_by(is_admin=False).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Email', 'Name', 'Joined', 'Orders', 'Total Spent'])
    for c in customers:
        writer.writerow([c.id, c.email, c.get_full_name(), c.created_at.strftime('%Y-%m-%d'), c.order_count, c.total_spent])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name=f'customers_{datetime.now().strftime("%Y%m%d")}.csv')

@admin_bp.route('/customers/<int:user_id>')
@admin_required
def customer_detail(user_id):
    customer = User.query.get_or_404(user_id)
    orders = Order.query.filter_by(user_id=customer.id).order_by(Order.created_at.desc()).all()
    return render_template('admin/customer_detail.html', customer=customer, orders=orders)

# ==================== COUPON MANAGEMENT ====================

@admin_bp.route('/coupons')
@admin_required
def manage_coupons():
    from app.models import Coupon
    coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return render_template('admin/coupons.html', coupons=coupons)

@admin_bp.route('/coupons/add', methods=['GET', 'POST'])
@admin_required
def add_coupon():
    from app.models import Coupon
    if request.method == 'POST':
        coupon = Coupon(
            code=request.form.get('code').upper(),
            description=request.form.get('description'),
            discount_type=request.form.get('discount_type'),
            discount_value=float(request.form.get('discount_value')),
            min_order_amount=float(request.form.get('min_order_amount', 0)),
            max_discount=float(request.form.get('max_discount')) if request.form.get('max_discount') else None,
            usage_limit=int(request.form.get('usage_limit')) if request.form.get('usage_limit') else None,
            per_user_limit=int(request.form.get('per_user_limit', 1)),
            valid_from=datetime.strptime(request.form.get('valid_from'), '%Y-%m-%d') if request.form.get('valid_from') else datetime.utcnow(),
            valid_until=datetime.strptime(request.form.get('valid_until'), '%Y-%m-%d') if request.form.get('valid_until') else None,
            is_active='is_active' in request.form
        )
        db.session.add(coupon)
        db.session.commit()
        flash(f'Coupon {coupon.code} added successfully!', 'success')
        return redirect(url_for('admin.manage_coupons'))
    return render_template('admin/add_coupon.html')

@admin_bp.route('/coupons/edit/<int:coupon_id>', methods=['GET', 'POST'])
@admin_required
def edit_coupon(coupon_id):
    from app.models import Coupon
    coupon = Coupon.query.get_or_404(coupon_id)
    if request.method == 'POST':
        coupon.code = request.form.get('code').upper()
        coupon.description = request.form.get('description')
        coupon.discount_type = request.form.get('discount_type')
        coupon.discount_value = float(request.form.get('discount_value'))
        coupon.min_order_amount = float(request.form.get('min_order_amount', 0))
        coupon.max_discount = float(request.form.get('max_discount')) if request.form.get('max_discount') else None
        coupon.usage_limit = int(request.form.get('usage_limit')) if request.form.get('usage_limit') else None
        coupon.per_user_limit = int(request.form.get('per_user_limit', 1))
        coupon.valid_from = datetime.strptime(request.form.get('valid_from'), '%Y-%m-%d') if request.form.get('valid_from') else datetime.utcnow()
        coupon.valid_until = datetime.strptime(request.form.get('valid_until'), '%Y-%m-%d') if request.form.get('valid_until') else None
        coupon.is_active = 'is_active' in request.form
        db.session.commit()
        flash(f'Coupon {coupon.code} updated successfully!', 'success')
        return redirect(url_for('admin.manage_coupons'))
    return render_template('admin/edit_coupon.html', coupon=coupon)

@admin_bp.route('/coupons/delete/<int:coupon_id>', methods=['POST'])
@admin_required
def delete_coupon(coupon_id):
    from app.models import Coupon
    coupon = Coupon.query.get_or_404(coupon_id)
    code = coupon.code
    db.session.delete(coupon)
    db.session.commit()
    flash(f'Coupon {code} deleted!', 'success')
    return redirect(url_for('admin.manage_coupons'))

@admin_bp.route('/coupons/toggle/<int:coupon_id>', methods=['POST'])
@admin_required
def toggle_coupon(coupon_id):
    from app.models import Coupon
    coupon = Coupon.query.get_or_404(coupon_id)
    coupon.is_active = not coupon.is_active
    db.session.commit()
    status = 'activated' if coupon.is_active else 'deactivated'
    flash(f'Coupon {coupon.code} {status}!', 'success')
    return redirect(url_for('admin.manage_coupons'))

# ==================== REVIEW MANAGEMENT ====================

@admin_bp.route('/reviews')
@admin_required
def manage_reviews():
    from app.models import Review
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    pending_count = Review.query.filter_by(is_approved=False).count()
    return render_template('admin/reviews.html', reviews=reviews, pending_count=pending_count)

@admin_bp.route('/reviews/approve/<int:review_id>', methods=['POST'])
@admin_required
def approve_review(review_id):
    from app.models import Review
    review = Review.query.get_or_404(review_id)
    review.is_approved = True
    db.session.commit()
    
    product = Product.query.get(review.product_id)
    if product:
        all_reviews = Review.query.filter_by(product_id=product.id, is_approved=True).all()
        if all_reviews:
            avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
            product.rating = avg_rating
            product.rating_count = len(all_reviews)
            db.session.commit()
    flash('Review approved!', 'success')
    return redirect(url_for('admin.manage_reviews'))

@admin_bp.route('/reviews/delete/<int:review_id>', methods=['POST'])
@admin_required
def delete_review(review_id):
    from app.models import Review
    review = Review.query.get_or_404(review_id)
    product_id = review.product_id
    db.session.delete(review)
    db.session.commit()
    
    product = Product.query.get(product_id)
    if product:
        all_reviews = Review.query.filter_by(product_id=product.id, is_approved=True).all()
        if all_reviews:
            avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
            product.rating = avg_rating
            product.rating_count = len(all_reviews)
        else:
            product.rating = 0
            product.rating_count = 0
        db.session.commit()
    flash('Review deleted!', 'success')
    return redirect(url_for('admin.manage_reviews'))

@admin_bp.route('/reviews/bulk-approve', methods=['POST'])
@admin_required
def bulk_approve_reviews():
    from app.models import Review
    review_ids = request.form.getlist('review_ids')
    if review_ids:
        Review.query.filter(Review.id.in_(review_ids)).update({'is_approved': True}, synchronize_session=False)
        db.session.commit()
        flash(f'{len(review_ids)} reviews approved!', 'success')
    return redirect(url_for('admin.manage_reviews'))

# ==================== NEWSLETTER MANAGEMENT ====================

@admin_bp.route('/newsletter')
@admin_required
def manage_newsletter():
    from app.models import NewsletterSubscriber
    subscribers = NewsletterSubscriber.query.filter_by(is_active=True).all()
    unsubscribed = NewsletterSubscriber.query.filter_by(is_active=False).all()
    return render_template('admin/newsletter.html', subscribers=subscribers, unsubscribed=unsubscribed)

@admin_bp.route('/newsletter/send', methods=['POST'])
@admin_required
def send_newsletter():
    from app.models import NewsletterSubscriber
    from flask_mail import Message
    from app import mail
    
    subject = request.form.get('subject')
    content = request.form.get('content')
    subscribers = NewsletterSubscriber.query.filter_by(is_active=True).all()
    
    count = 0
    for sub in subscribers:
        try:
            msg = Message(subject, recipients=[sub.email])
            msg.html = content
            mail.send(msg)
            count += 1
        except:
            pass
    flash(f'Newsletter sent to {count} subscribers', 'success')
    return redirect(url_for('admin.manage_newsletter'))

@admin_bp.route('/newsletter/remove/<int:subscriber_id>', methods=['POST'])
@admin_required
def remove_subscriber(subscriber_id):
    from app.models import NewsletterSubscriber
    subscriber = NewsletterSubscriber.query.get_or_404(subscriber_id)
    db.session.delete(subscriber)
    db.session.commit()
    flash('Subscriber removed', 'success')
    return redirect(url_for('admin.manage_newsletter'))

# ==================== REPORTS ====================

@admin_bp.route('/reports')
@admin_required
def reports():
    return render_template('admin/reports.html')

# ==================== CHAT ====================

@admin_bp.route('/chat')
@admin_required
def chat_dashboard():
    return render_template('admin/chat_dashboard.html')

@admin_bp.route('/coupons/reset-usage/<int:coupon_id>', methods=['POST'])
@admin_required
def reset_coupon_usage(coupon_id):
    """Reset coupon usage count"""
    from app.models import Coupon, CouponUsage
    
    coupon = Coupon.query.get_or_404(coupon_id)
    coupon.used_count = 0
    
    # Delete all usage records
    CouponUsage.query.filter_by(coupon_id=coupon_id).delete()
    
    db.session.commit()
    flash(f'Usage count for {coupon.code} has been reset', 'success')
    return redirect(url_for('admin.manage_coupons'))