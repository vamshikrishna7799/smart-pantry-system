from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import pantry_items_collection, users_collection, profiles_collection
from services.email_service import send_low_stock_alert, send_expiry_alert, send_shopping_list_email
from bson import ObjectId
from datetime import datetime, timedelta

pantry_bp = Blueprint('pantry', __name__)

@pantry_bp.route('/add-item', methods=['POST'])
@jwt_required()
def add_item():
    """Add a new pantry item"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        item_name = data.get('item_name')
        quantity = data.get('quantity', 1)
        expiry_date = data.get('expiry_date')
        storage_type = data.get('storage_type')
        profile_id = data.get('profile_id')
        
        if not all([item_name, storage_type, profile_id]):
            return jsonify({'message': 'Missing required fields'}), 400
        
        # Parse expiry date if provided
        expiry = None
        if expiry_date:
            try:
                expiry = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            except:
                try:
                    expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
                except:
                    return jsonify({'message': 'Invalid date format'}), 400
        
        # Check if item already exists in this profile
        existing = pantry_items_collection.find_one({
            'user_id': ObjectId(user_id),
            'profile_id': profile_id,
            'name': item_name,
            'storage_type': storage_type,
            'status': 'active'
        })
        
        if existing:
            # Update quantity instead of creating new
            new_quantity = existing['quantity'] + quantity
            pantry_items_collection.update_one(
                {'_id': existing['_id']},
                {
                    '$set': {
                        'quantity': new_quantity,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Check for low stock after update
            if new_quantity <= 2 and not existing.get('low_stock_notified'):
                user = users_collection.find_one({'_id': ObjectId(user_id)})
                if user and user.get('email'):
                    send_low_stock_alert(user['email'], existing)
                    pantry_items_collection.update_one(
                        {'_id': existing['_id']},
                        {'$set': {'low_stock_notified': True}}
                    )
            
            return jsonify({'message': 'Item quantity updated'}), 200
        
        # Create new item
        new_item = {
            'user_id': ObjectId(user_id),
            'profile_id': profile_id,
            'name': item_name,
            'quantity': quantity,
            'unit': 'pcs',
            'storage_type': storage_type,
            'expiry_date': expiry,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'status': 'active',
            'notification_sent': False,
            'low_stock_notified': False
        }
        
        result = pantry_items_collection.insert_one(new_item)
        
        # Check if item is already expired and send notification
        if expiry and expiry < datetime.utcnow():
            user = users_collection.find_one({'_id': ObjectId(user_id)})
            if user and user.get('email'):
                send_expiry_alert(user['email'], new_item, 'expired')
                pantry_items_collection.update_one(
                    {'_id': result.inserted_id},
                    {'$set': {'notification_sent': True}}
                )
        # Check if item is expiring soon (within 3 days)
        elif expiry and expiry <= datetime.utcnow() + timedelta(days=3):
            user = users_collection.find_one({'_id': ObjectId(user_id)})
            if user and user.get('email'):
                send_expiry_alert(user['email'], new_item, 'expiring')
                pantry_items_collection.update_one(
                    {'_id': result.inserted_id},
                    {'$set': {'notification_sent': True}}
                )
        
        return jsonify({
            'message': 'Item added successfully',
            'item_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        print(f"Add item error: {e}")
        return jsonify({'message': 'Server error'}), 500

@pantry_bp.route('/get-items', methods=['GET'])
@jwt_required()
def get_items():
    """Get all pantry items for a specific profile"""
    try:
        user_id = get_jwt_identity()
        profile_id = request.args.get('profile_id')
        
        if not profile_id:
            return jsonify({'message': 'Profile ID required'}), 400
        
        # Get all active items for this profile
        items = list(pantry_items_collection.find({
            'user_id': ObjectId(user_id),
            'profile_id': profile_id,
            'status': 'active'
        }).sort('created_at', -1))
        
        # Format items for response
        formatted_items = []
        now = datetime.utcnow()
        
        for item in items:
            expiry_date = item.get('expiry_date')
            days_left = None
            status = 'Good'
            
            if expiry_date:
                days_diff = (expiry_date - now).days
                if days_diff < 0:
                    status = 'Expired'
                elif days_diff <= 3:
                    status = 'Expiring Soon'
                elif days_diff <= 7:
                    status = 'Near Expiry'
                else:
                    status = 'Good'
                days_left = days_diff
            
            # Override status based on quantity
            if item['quantity'] == 0:
                status = 'Out of Stock'
            elif item['quantity'] <= 2 and status != 'Expired':
                status = 'Low Stock'
            
            formatted_items.append({
                '_id': str(item['_id']),
                'item_name': item['name'],
                'quantity': item['quantity'],
                'unit': item.get('unit', 'pcs'),
                'storage_type': item['storage_type'],
                'expiry_date': expiry_date.isoformat() if expiry_date else None,
                'days_left': days_left,
                'status': status,
                'created_at': item['created_at'].isoformat()
            })
        
        return jsonify(formatted_items), 200
        
    except Exception as e:
        print(f"Get items error: {e}")
        return jsonify({'message': 'Server error'}), 500

@pantry_bp.route('/update-item/<item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    """Update an item (quantity, etc)"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        update_data = {'updated_at': datetime.utcnow()}
        
        if 'quantity' in data:
            update_data['quantity'] = data['quantity']
            # Reset low stock notification if quantity increased
            if data['quantity'] > 2:
                update_data['low_stock_notified'] = False
        
        if 'expiry_date' in data:
            if data['expiry_date']:
                try:
                    update_data['expiry_date'] = datetime.fromisoformat(data['expiry_date'].replace('Z', '+00:00'))
                except:
                    update_data['expiry_date'] = datetime.strptime(data['expiry_date'], '%Y-%m-%d')
                # Reset expiry notification if date changed
                update_data['notification_sent'] = False
            else:
                update_data['expiry_date'] = None
                update_data['notification_sent'] = False
        
        result = pantry_items_collection.update_one(
            {
                '_id': ObjectId(item_id),
                'user_id': ObjectId(user_id)
            },
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Get updated item
            item = pantry_items_collection.find_one({'_id': ObjectId(item_id)})
            
            # Check for low stock alert
            if 'quantity' in data and data['quantity'] <= 2 and data['quantity'] > 0 and not item.get('low_stock_notified'):
                user = users_collection.find_one({'_id': ObjectId(user_id)})
                if user and user.get('email'):
                    send_low_stock_alert(user['email'], item)
                    pantry_items_collection.update_one(
                        {'_id': ObjectId(item_id)},
                        {'$set': {'low_stock_notified': True}}
                    )
            
            # Check for expiry alerts
            if item.get('expiry_date'):
                now = datetime.utcnow()
                if item['expiry_date'] < now and not item.get('notification_sent'):
                    user = users_collection.find_one({'_id': ObjectId(user_id)})
                    if user and user.get('email'):
                        send_expiry_alert(user['email'], item, 'expired')
                        pantry_items_collection.update_one(
                            {'_id': ObjectId(item_id)},
                            {'$set': {'notification_sent': True}}
                        )
                elif item['expiry_date'] <= now + timedelta(days=3) and not item.get('notification_sent'):
                    user = users_collection.find_one({'_id': ObjectId(user_id)})
                    if user and user.get('email'):
                        send_expiry_alert(user['email'], item, 'expiring')
                        pantry_items_collection.update_one(
                            {'_id': ObjectId(item_id)},
                            {'$set': {'notification_sent': True}}
                        )
            
            return jsonify({'message': 'Item updated successfully'}), 200
        else:
            return jsonify({'message': 'Item not found'}), 404
            
    except Exception as e:
        print(f"Update item error: {e}")
        return jsonify({'message': 'Server error'}), 500

@pantry_bp.route('/delete-item/<item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    """Delete an item (soft delete)"""
    try:
        user_id = get_jwt_identity()
        
        # Soft delete - just mark as inactive
        result = pantry_items_collection.update_one(
            {
                '_id': ObjectId(item_id),
                'user_id': ObjectId(user_id)
            },
            {
                '$set': {
                    'status': 'deleted',
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            return jsonify({'message': 'Item deleted successfully'}), 200
        else:
            return jsonify({'message': 'Item not found'}), 404
            
    except Exception as e:
        print(f"Delete item error: {e}")
        return jsonify({'message': 'Server error'}), 500

@pantry_bp.route('/get-expiring-items', methods=['GET'])
@jwt_required()
def get_expiring_items():
    """Get items expiring soon for notifications"""
    try:
        user_id = get_jwt_identity()
        profile_id = request.args.get('profile_id')
        
        now = datetime.utcnow()
        three_days_later = now + timedelta(days=3)
        
        query = {
            'user_id': ObjectId(user_id),
            'status': 'active',
            'expiry_date': {'$gte': now, '$lte': three_days_later}
        }
        
        if profile_id:
            query['profile_id'] = profile_id
        
        items = list(pantry_items_collection.find(query))
        
        formatted_items = []
        for item in items:
            formatted_items.append({
                '_id': str(item['_id']),
                'name': item['name'],
                'quantity': item['quantity'],
                'expiry_date': item['expiry_date'].isoformat(),
                'profile_id': item['profile_id']
            })
        
        return jsonify(formatted_items), 200
        
    except Exception as e:
        print(f"Get expiring items error: {e}")
        return jsonify({'message': 'Server error'}), 500

@pantry_bp.route('/email-shopping-list', methods=['POST'])
@jwt_required()
def email_shopping_list():
    """Email shopping list to user"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        email = data.get('email')
        items = data.get('items', [])
        profile_name = data.get('profile_name', 'Unknown')
        
        if not items:
            return jsonify({'message': 'No items in shopping list'}), 400
        
        # Get user's email if not provided
        if not email:
            user = users_collection.find_one({'_id': ObjectId(user_id)})
            if user:
                email = user.get('email')
            
            if not email:
                return jsonify({'message': 'No email address found for user'}), 400
        
        # Send email
        success = send_shopping_list_email(email, items, profile_name)
        
        if success:
            return jsonify({'message': 'Shopping list sent successfully'}), 200
        else:
            return jsonify({'message': 'Failed to send email. Check server logs.'}), 500
            
    except Exception as e:
        print(f"Email shopping list error: {e}")
        return jsonify({'message': f'Server error: {str(e)}'}), 500

@pantry_bp.route('/bulk-add-items', methods=['POST'])
@jwt_required()
def bulk_add_items():
    """Add multiple items at once"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        items = data.get('items', [])
        profile_id = data.get('profile_id')
        
        if not items or not profile_id:
            return jsonify({'message': 'Items and profile_id required'}), 400
        
        added_count = 0
        updated_count = 0
        
        for item_data in items:
            item_name = item_data.get('item_name')
            quantity = item_data.get('quantity', 1)
            expiry_date = item_data.get('expiry_date')
            storage_type = item_data.get('storage_type', 'refrigerator')
            
            if not item_name:
                continue
            
            # Parse expiry date
            expiry = None
            if expiry_date:
                try:
                    expiry = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                except:
                    try:
                        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
                    except:
                        pass
            
            # Check if exists
            existing = pantry_items_collection.find_one({
                'user_id': ObjectId(user_id),
                'profile_id': profile_id,
                'name': item_name,
                'storage_type': storage_type,
                'status': 'active'
            })
            
            if existing:
                # Update
                new_quantity = existing['quantity'] + quantity
                pantry_items_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {
                        'quantity': new_quantity,
                        'updated_at': datetime.utcnow()
                    }}
                )
                updated_count += 1
            else:
                # Insert new
                new_item = {
                    'user_id': ObjectId(user_id),
                    'profile_id': profile_id,
                    'name': item_name,
                    'quantity': quantity,
                    'unit': 'pcs',
                    'storage_type': storage_type,
                    'expiry_date': expiry,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                    'status': 'active',
                    'notification_sent': False,
                    'low_stock_notified': False
                }
                pantry_items_collection.insert_one(new_item)
                added_count += 1
        
        return jsonify({
            'message': f'Bulk add complete: {added_count} added, {updated_count} updated',
            'added': added_count,
            'updated': updated_count
        }), 200
        
    except Exception as e:
        print(f"Bulk add error: {e}")
        return jsonify({'message': 'Server error'}), 500

@pantry_bp.route('/search-items', methods=['GET'])
@jwt_required()
def search_items():
    """Search items by name"""
    try:
        user_id = get_jwt_identity()
        query = request.args.get('q', '')
        profile_id = request.args.get('profile_id')
        
        if not query:
            return jsonify([]), 200
        
        search_filter = {
            'user_id': ObjectId(user_id),
            'status': 'active',
            'name': {'$regex': query, '$options': 'i'}
        }
        
        if profile_id:
            search_filter['profile_id'] = profile_id
        
        items = list(pantry_items_collection.find(search_filter).limit(10))
        
        results = []
        for item in items:
            results.append({
                '_id': str(item['_id']),
                'name': item['name'],
                'quantity': item['quantity'],
                'storage_type': item['storage_type'],
                'profile_id': item['profile_id']
            })
        
        return jsonify(results), 200
        
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'message': 'Server error'}), 500

@pantry_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    """Get pantry statistics for a profile"""
    try:
        user_id = get_jwt_identity()
        profile_id = request.args.get('profile_id')
        
        if not profile_id:
            return jsonify({'message': 'Profile ID required'}), 400
        
        now = datetime.utcnow()
        
        # Get all active items
        items = list(pantry_items_collection.find({
            'user_id': ObjectId(user_id),
            'profile_id': profile_id,
            'status': 'active'
        }))
        
        total_items = len(items)
        total_quantity = sum(item['quantity'] for item in items)
        
        # Count by status
        expired = 0
        expiring_soon = 0
        low_stock = 0
        out_of_stock = 0
        good = 0
        
        for item in items:
            if item['quantity'] == 0:
                out_of_stock += 1
            elif item['quantity'] <= 2:
                low_stock += 1
            
            if item.get('expiry_date'):
                days_left = (item['expiry_date'] - now).days
                if days_left < 0:
                    expired += 1
                elif days_left <= 3:
                    expiring_soon += 1
        
        # Count by storage type
        fridge_items = sum(1 for item in items if item['storage_type'] == 'refrigerator')
        freezer_items = sum(1 for item in items if item['storage_type'] == 'freezer')
        
        return jsonify({
            'total_items': total_items,
            'total_quantity': total_quantity,
            'expired': expired,
            'expiring_soon': expiring_soon,
            'low_stock': low_stock,
            'out_of_stock': out_of_stock,
            'good_condition': good,
            'fridge_items': fridge_items,
            'freezer_items': freezer_items
        }), 200
        
    except Exception as e:
        print(f"Stats error: {e}")
        return jsonify({'message': 'Server error'}), 500