# routes/analytics_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.analytics_service import analytics
from bson import ObjectId

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/train-model', methods=['POST'])
@jwt_required()
def train_model():
    """Train ML model for expiry prediction"""
    user_id = get_jwt_identity()
    
    success, result = analytics.train_model(user_id)
    
    if success:
        return jsonify({
            'message': 'Model trained successfully',
            'data': result
        }), 200
    else:
        return jsonify({'message': result}), 400

@analytics_bp.route('/predict-expiry', methods=['POST'])
@jwt_required()
def predict_expiry():
    """Predict when an item will expire"""
    user_id = get_jwt_identity()
    data = request.json
    
    item_name = data.get('item_name')
    quantity = data.get('quantity', 1)
    storage_type = data.get('storage_type', 'refrigerator')
    
    if not item_name:
        return jsonify({'message': 'Item name required'}), 400
    
    predicted_days, error = analytics.predict_expiry(user_id, item_name, quantity, storage_type)
    
    if predicted_days:
        expiry_date = datetime.utcnow() + timedelta(days=predicted_days)
        return jsonify({
            'predicted_days': predicted_days,
            'predicted_expiry_date': expiry_date.strftime('%Y-%m-%d'),
            'confidence': 'high' if predicted_days < 14 else 'medium'
        }), 200
    else:
        return jsonify({'message': error or 'Could not predict expiry'}), 400

@analytics_bp.route('/suggest-quantity', methods=['POST'])
@jwt_required()
def suggest_quantity():
    """Suggest optimal purchase quantity"""
    user_id = get_jwt_identity()
    data = request.json
    
    item_name = data.get('item_name')
    
    if not item_name:
        return jsonify({'message': 'Item name required'}), 400
    
    suggested_qty, reason = analytics.suggest_purchase_quantity(user_id, item_name)
    
    return jsonify({
        'item_name': item_name,
        'suggested_quantity': suggested_qty,
        'reason': reason
    }), 200

@analytics_bp.route('/consumption-patterns', methods=['GET'])
@jwt_required()
def consumption_patterns():
    """Get consumption patterns"""
    user_id = get_jwt_identity()
    profile_id = request.args.get('profile_id')
    
    patterns = analytics.get_consumption_patterns(user_id, profile_id)
    
    if patterns:
        return jsonify(patterns), 200
    else:
        return jsonify({'message': 'No data available'}), 404

@analytics_bp.route('/waste-report', methods=['GET'])
@jwt_required()
def waste_report():
    """Generate waste reduction report"""
    user_id = get_jwt_identity()
    profile_id = request.args.get('profile_id')
    
    query = {'user_id': ObjectId(user_id), 'status': 'active'}
    if profile_id:
        query['profile_id'] = profile_id
    
    items = list(pantry_items_collection.find(query))
    
    # Calculate waste statistics
    total_items = len(items)
    expired_items = 0
    wasted_quantity = 0
    total_value_lost = 0
    
    # Approximate value per item type
    item_values = {
        'meat': 10,
        'dairy': 5,
        'vegetables': 3,
        'fruits': 4,
        'frozen': 6,
        'canned': 2,
        'dry': 3,
        'other': 4
    }
    
    waste_by_category = {}
    
    for item in items:
        category = analytics.categorize_item(item['name'])
        if category not in waste_by_category:
            waste_by_category[category] = {
                'total': 0,
                'expired': 0,
                'value_lost': 0
            }
        
        waste_by_category[category]['total'] += 1
        
        if item.get('expiry_date') and item['expiry_date'] < datetime.utcnow():
            expired_items += 1
            wasted_quantity += item['quantity']
            value = item_values.get(category, 4) * item['quantity']
            total_value_lost += value
            
            waste_by_category[category]['expired'] += 1
            waste_by_category[category]['value_lost'] += value
    
    waste_rate = expired_items / total_items if total_items > 0 else 0
    
    # Generate recommendations
    recommendations = []
    
    if waste_rate > 0.3:
        recommendations.append("⚠️ High waste rate detected! Consider buying smaller quantities more frequently.")
    
    for category, data in waste_by_category.items():
        if data['total'] > 0 and data['expired'] / data['total'] > 0.4:
            recommendations.append(f"🍎 {category.capitalize()} items have high waste rate. Buy only what you need.")
    
    if wasted_quantity > 10:
        recommendations.append("💰 You've wasted significant quantity. Try meal planning to reduce waste.")
    
    return jsonify({
        'total_items': total_items,
        'expired_items': expired_items,
        'waste_rate': round(waste_rate * 100, 2),
        'wasted_quantity': wasted_quantity,
        'estimated_value_lost': round(total_value_lost, 2),
        'waste_by_category': waste_by_category,
        'recommendations': recommendations
    }), 200