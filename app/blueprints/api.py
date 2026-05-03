from flask import Blueprint, jsonify
from app.models import Product

api_bp = Blueprint('api', __name__)

@api_bp.route('/products')
def get_products():
    """Get all products"""
    products = Product.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'slug': p.slug,
        'price': p.price,
        'description': p.short_description,
        'image': p.image_url,
        'stock': p.stock_quantity
    } for p in products])

@api_bp.route('/products/<int:product_id>')
def get_product(product_id):
    """Get single product"""
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'slug': product.slug,
        'price': product.price,
        'description': product.description,
        'image': product.image_url,
        'stock': product.stock_quantity,
        'category_id': product.category_id
    })

@api_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'API is running'})
