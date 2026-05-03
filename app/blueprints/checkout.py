from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.models import Order, OrderItem, Product, db
from datetime import datetime
import secrets

checkout_bp = Blueprint('checkout', __name__)

# Nigerian states with shipping costs
NIGERIAN_STATES = [
    'Abia', 'Abuja FCT', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue',
    'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'Gombe', 'Imo',
    'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos', 'Nasarawa',
    'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara'
]

# Shipping cost by zone (in NGN)
SHIPPING_COSTS = {
    'Lagos': 2500,
    'Ogun': 2500,
    'Oyo': 3000,
    'Abuja FCT': 3500,
    'Rivers': 4000,
    'Delta': 4000,
    'Kano': 4500,
    'Kaduna': 4500,
    'Others': 5000
}

def generate_order_number():
    """Generate unique order number"""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    random_suffix = secrets.token_hex(4).upper()
    return f"NG-ORD-{timestamp}-{random_suffix}"

@checkout_bp.route('/')
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart.view_cart'))
    
    items = []
    subtotal = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            item_total = product.price * qty
            subtotal += item_total
            items.append({'product': product, 'quantity': qty, 'total': item_total})
    
    # Apply coupon discount
    discount = 0
    coupon_code = None
    coupon_data = session.get('coupon')
    if coupon_data:
        discount = coupon_data.get('discount', 0)
        coupon_code = coupon_data.get('code')
        subtotal_after_discount = subtotal - discount
    else:
        subtotal_after_discount = subtotal
    
    # Nigerian shipping calculation
    shipping_cost = 2500
    if subtotal_after_discount >= 50000:
        shipping_cost = 0
    
    vat = subtotal_after_discount * 0.075
    total = subtotal_after_discount + shipping_cost + vat
    
    return render_template('checkout/shipping.html',
                         cart_items=items,
                         subtotal=subtotal,
                         discount=discount,
                         coupon_code=coupon_code,
                         subtotal_after_discount=subtotal_after_discount,
                         shipping_cost=shipping_cost,
                         vat=vat,
                         total=total)
    
@checkout_bp.route('/calculate-shipping', methods=['POST'])
def calculate_shipping():
    """Calculate shipping cost based on state"""
    data = request.get_json()
    state = data.get('state')
    
    shipping_cost = SHIPPING_COSTS.get(state, SHIPPING_COSTS.get('Others', 5000))
    
    return jsonify({
        'shipping_cost': shipping_cost,
        'state': state
    })

@checkout_bp.route('/process', methods=['POST'])
@login_required
def process_order():
    from app.models import Coupon, CouponUsage
    
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('cart.view_cart'))
    
    # Cart calculation
    subtotal = 0
    order_items = []
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product and product.is_active:
            if product.stock_quantity < qty:
                flash(f'Insufficient stock for {product.name}', 'danger')
                return redirect(url_for('cart.view_cart'))
            item_total = product.price * qty
            subtotal += item_total
            order_items.append({
                'product': product,
                'quantity': qty,
                'price': product.price,
                'total': item_total
            })
    
    # Apply coupon discount
    discount = 0
    coupon_code = None
    coupon_id = None
    coupon_data = session.get('coupon')
    
    if coupon_data:
        coupon_code = coupon_data.get('code')
        coupon_id = coupon_data.get('coupon_id')
        discount = coupon_data.get('discount', 0)
        
        # Verify coupon is still valid before finalizing
        coupon = Coupon.query.get(coupon_id)
        if coupon and coupon.can_use(current_user.id):
            coupon_discount = coupon.calculate_discount(subtotal, current_user.id)
            if coupon_discount != discount:
                discount = coupon_discount
        else:
            # Coupon no longer valid, remove it
            session.pop('coupon', None)
            coupon_code = None
            discount = 0
            flash('Your coupon is no longer valid', 'warning')
    
    subtotal_after_discount = subtotal - discount
    
    # Calculate shipping and tax
    shipping_state = request.form.get('shipping_state')
    shipping_cost = 2500
    if shipping_state == 'Lagos':
        shipping_cost = 2500
    elif shipping_state == 'Ogun':
        shipping_cost = 2500
    elif shipping_state == 'Oyo':
        shipping_cost = 3000
    elif shipping_state == 'Abuja FCT':
        shipping_cost = 3500
    elif shipping_state in ['Rivers', 'Delta']:
        shipping_cost = 4000
    elif shipping_state in ['Kano', 'Kaduna']:
        shipping_cost = 4500
    else:
        shipping_cost = 5000
    
    if subtotal_after_discount >= 50000:
        shipping_cost = 0
    
    vat = subtotal_after_discount * 0.075
    total = subtotal_after_discount + shipping_cost + vat
    
    # Create order
    order = Order(
        user_id=current_user.id,
        order_number=generate_order_number(),
        status='pending',
        payment_status='pending',
        payment_method=request.form.get('payment_method', 'cash_on_delivery'),
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=vat,
        discount=discount,
        coupon_code=coupon_code,
        total=total,
        shipping_name=request.form.get('shipping_name'),
        shipping_address=request.form.get('shipping_address'),
        shipping_city=request.form.get('shipping_city'),
        shipping_state=shipping_state,
        shipping_postal_code=request.form.get('shipping_postal_code', ''),
        shipping_country='Nigeria',
        shipping_phone=request.form.get('shipping_phone'),
        shipping_email=request.form.get('shipping_email'),
        notes=request.form.get('notes')
    )
    db.session.add(order)
    db.session.flush()
    
    # Create order items and update stock
    for item in order_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item['product'].id,
            quantity=item['quantity'],
            price=item['price'],
            product_name=item['product'].name,
            product_image=item['product'].image_url,
            total=item['total']
        )
        db.session.add(order_item)
        item['product'].stock_quantity -= item['quantity']
        item['product'].sales_count += item['quantity']
    
    # Record coupon usage if coupon was applied
    if coupon_id and discount > 0:
        coupon = Coupon.query.get(coupon_id)
        if coupon:
            # Increment usage count
            coupon.used_count += 1
            
            # Record user usage
            usage = CouponUsage(
                coupon_id=coupon.id,
                user_id=current_user.id,
                order_id=order.id,
                discount_amount=discount
            )
            db.session.add(usage)
    
    # Update user stats
    current_user.order_count += 1
    current_user.total_spent += total
    
    db.session.commit()
    
    # Clear cart and coupon from session
    session.pop('cart', None)
    session.pop('coupon', None)
    
    flash(f'Order placed successfully! Your order number is {order.order_number}', 'success')
    return redirect(url_for('user.order_detail', order_id=order.id))