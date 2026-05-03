from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import User, Order, Wishlist, Product, db

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """Customer dashboard"""
    recent_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    wishlist_count = Wishlist.query.filter_by(user_id=current_user.id).count()
    total_orders = Order.query.filter_by(user_id=current_user.id).count()
    total_spent = db.session.query(db.func.sum(Order.total)).filter_by(user_id=current_user.id).scalar() or 0
    
    return render_template('user/dashboard.html',
                         recent_orders=recent_orders,
                         wishlist_count=wishlist_count,
                         total_orders=total_orders,
                         total_spent=total_spent)

@user_bp.route('/orders')
@login_required
def orders():
    """Order history"""
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('user/orders.html', orders=orders)

@user_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Order details page"""
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))
    
    return render_template('user/order_detail.html', order=order)

@user_bp.route('/profile')
@login_required
def profile():
    """View profile"""
    return render_template('user/profile.html', user=current_user)

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit profile"""
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.phone = request.form.get('phone')
        current_user.address = request.form.get('address')
        current_user.city = request.form.get('city')
        current_user.state = request.form.get('state')
        current_user.postal_code = request.form.get('postal_code')
        current_user.country = request.form.get('country')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user.profile'))
    
    return render_template('user/edit_profile.html', user=current_user)

@user_bp.route('/wishlist')
@login_required
def wishlist():
    """View wishlist"""
    wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).options(db.joinedload(Wishlist.product)).all()
    return render_template('user/wishlist.html', wishlist_items=wishlist_items)

@user_bp.route('/wishlist/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_wishlist(product_id):
    """Add product to wishlist"""
    existing = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if existing:
        flash('Product already in wishlist', 'info')
    else:
        wishlist_item = Wishlist(user_id=current_user.id, product_id=product_id)
        db.session.add(wishlist_item)
        db.session.commit()
        flash('Product added to wishlist!', 'success')
    
    return redirect(request.referrer or url_for('user.wishlist'))

@user_bp.route('/wishlist/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_wishlist(product_id):
    """Remove product from wishlist"""
    wishlist_item = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if wishlist_item:
        db.session.delete(wishlist_item)
        db.session.commit()
        flash('Product removed from wishlist', 'success')
    
    return redirect(url_for('user.wishlist'))
