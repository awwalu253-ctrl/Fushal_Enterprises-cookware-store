from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from app.models import Product, Coupon
from app.models import db

cart_bp = Blueprint('cart', __name__)

def get_cart():
    """Get current cart from session"""
    return session.get('cart', {})

def save_cart(cart):
    """Save cart to session"""
    session['cart'] = cart
    session.modified = True

def calculate_cart_total(cart):
    """Calculate cart total with prices from database"""
    total = 0
    items = []
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product and product.is_active:
            item_total = product.price * quantity
            total += item_total
            items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
    return total, items

@cart_bp.route('/')
def view_cart():
    """View cart page"""
    cart = get_cart()
    total, items = calculate_cart_total(cart)
    
    # Apply coupon discount if exists
    discount = 0
    coupon_data = session.get('coupon')
    if coupon_data:
        discount = coupon_data.get('discount', 0)
    
    final_total = total - discount
    
    return render_template('cart/cart.html', 
                         cart_items=items, 
                         cart_total=total,
                         discount=discount,
                         final_total=final_total,
                         coupon=session.get('coupon'))

@cart_bp.route('/add', methods=['POST'])
def add_to_cart():
    """Add product to cart"""
    product_id = request.json.get('product_id') or request.form.get('product_id')
    quantity = int(request.json.get('quantity', 1) or request.form.get('quantity', 1))
    
    if not product_id:
        return jsonify({'success': False, 'error': 'Product ID required'})
    
    product = Product.query.get(product_id)
    if not product or not product.is_active:
        return jsonify({'success': False, 'error': 'Product not found'})
    
    if product.stock_quantity < quantity:
        return jsonify({'success': False, 'error': f'Only {product.stock_quantity} items in stock'})
    
    cart = get_cart()
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    save_cart(cart)
    
    cart_count = sum(cart.values())
    return jsonify({'success': True, 'cart_count': cart_count, 'message': 'Product added to cart'})

@cart_bp.route('/update', methods=['POST'])
def update_cart():
    """Update cart item quantity"""
    product_id = str(request.json.get('product_id'))
    quantity = int(request.json.get('quantity', 1))
    
    cart = get_cart()
    
    if quantity <= 0:
        cart.pop(product_id, None)
    else:
        product = Product.query.get(int(product_id))
        if product and product.stock_quantity >= quantity:
            cart[product_id] = quantity
        else:
            return jsonify({'success': False, 'error': 'Insufficient stock'})
    
    save_cart(cart)
    total, items = calculate_cart_total(cart)
    
    return jsonify({
        'success': True,
        'cart_count': sum(cart.values()),
        'cart_total': total
    })

@cart_bp.route('/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    """Remove item from cart"""
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    
    flash('Item removed from cart', 'success')
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/clear')
def clear_cart():
    """Clear entire cart"""
    session.pop('cart', None)
    session.pop('coupon', None)
    flash('Cart cleared', 'info')
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/apply-coupon', methods=['POST'])
def apply_coupon():
    """Apply coupon code to cart"""
    from app.models import Coupon
    import traceback
    
    try:
        coupon_code = request.form.get('coupon_code', '').strip().upper()
        print(f"DEBUG: Received coupon code: '{coupon_code}'")
        
        cart = get_cart()
        print(f"DEBUG: Cart contents: {cart}")
        
        if not cart:
            return jsonify({'success': False, 'error': 'Your cart is empty'})
        
        # Calculate subtotal
        subtotal = 0
        for product_id, quantity in cart.items():
            product = Product.query.get(int(product_id))
            if product:
                subtotal += product.price * quantity
        
        print(f"DEBUG: Cart subtotal: {subtotal}")
        
        # Find coupon
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        print(f"DEBUG: Coupon found: {coupon}")
        
        if not coupon:
            return jsonify({'success': False, 'error': f'Coupon "{coupon_code}" not found'})
        
        # Check if coupon is active
        if not coupon.is_active:
            return jsonify({'success': False, 'error': 'This coupon is not active'})
        
        # Check if coupon is valid (not expired)
        from datetime import datetime
        now = datetime.utcnow()
        if coupon.valid_until and now > coupon.valid_until:
            return jsonify({'success': False, 'error': f'Coupon expired on {coupon.valid_until.strftime("%Y-%m-%d")}'})
        
        if now < coupon.valid_from:
            return jsonify({'success': False, 'error': f'Coupon valid from {coupon.valid_from.strftime("%Y-%m-%d")}'})
        
        # Check usage limit
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            return jsonify({'success': False, 'error': 'Coupon usage limit has been reached'})
        
        # Check minimum order
        if subtotal < coupon.min_order_amount:
            return jsonify({'success': False, 'error': f'Minimum order of ₦{coupon.min_order_amount:,.2f} required (Current: ₦{subtotal:,.2f})'})
        
        # Calculate discount
        if coupon.discount_type == 'percentage':
            discount = subtotal * (coupon.discount_value / 100)
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else:
            discount = min(coupon.discount_value, subtotal)
        
        print(f"DEBUG: Discount calculated: {discount}")
        
        if discount <= 0:
            return jsonify({'success': False, 'error': 'Coupon does not provide any discount'})
        
        # Store coupon in session
        session['coupon'] = {
            'code': coupon.code,
            'discount': discount,
            'coupon_id': coupon.id
        }
        
        print(f"DEBUG: Coupon stored in session: {session.get('coupon')}")
        
        return jsonify({
            'success': True, 
            'message': f'Coupon {coupon_code} applied! You saved ₦{discount:,.2f}',
            'discount': discount
        })
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

@cart_bp.route('/remove-coupon', methods=['POST'])
def remove_coupon():
    """Remove applied coupon"""
    session.pop('coupon', None)
    flash('Coupon removed', 'info')
    return redirect(url_for('cart.view_cart'))