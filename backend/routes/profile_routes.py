from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import profiles_collection, pantry_items_collection
from bson import ObjectId
from datetime import datetime

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/get-profiles', methods=['GET'])
@jwt_required()
def get_profiles():
    """Get all profiles for the logged-in user"""
    try:
        user_id = get_jwt_identity()
        
        profiles = list(profiles_collection.find({'user_id': ObjectId(user_id)}))
        
        # Default emoji map for profiles
        default_emoji = {
            'home': '🏠',
            'office': '🏢',
            'factory': '🏭',
            'lab': '🍙',
            'test': '🧆'
        }
        
        # Format profiles for response
        formatted_profiles = []
        for profile in profiles:
            profile_name = profile['profile_name']
            formatted_profiles.append({
                '_id': str(profile['_id']),
                'profile_name': profile_name,
                'display_name': profile.get('display_name', profile_name.capitalize() + ' Pantry'),
                'emoji': profile.get('emoji', default_emoji.get(profile_name, '📦')),
                'created_at': profile.get('created_at', datetime.utcnow()).isoformat()
            })
        
        return jsonify(formatted_profiles), 200
        
    except Exception as e:
        print(f"Get profiles error: {e}")
        return jsonify({'message': 'Server error'}), 500

@profile_bp.route('/add-profile', methods=['POST'])
@jwt_required()
def add_profile():
    """Add a new profile"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        profile_name = data.get('profile_name')
        display_name = data.get('display_name')
        
        if not profile_name:
            return jsonify({'message': 'Profile name required'}), 400
        
        # Check if profile already exists
        existing = profiles_collection.find_one({
            'user_id': ObjectId(user_id),
            'profile_name': profile_name
        })
        
        if existing:
            return jsonify({'message': 'Profile already exists'}), 409
        
        # Check maximum profiles (limit to 5)
        count = profiles_collection.count_documents({'user_id': ObjectId(user_id)})
        if count >= 5:
            return jsonify({'message': 'Maximum 5 profiles allowed'}), 400
        
        # Emoji options for custom profiles
        emoji_options = ['🍙', '🥨', '🧀', '🍉', '🍒', '🥭', '🧆', '🫐', '🍑', '🥥']
        import random
        random_emoji = random.choice(emoji_options)
        
        # Create new profile
        new_profile = {
            'user_id': ObjectId(user_id),
            'profile_name': profile_name,
            'display_name': display_name or f"{profile_name.capitalize()} Pantry",
            'emoji': random_emoji,
            'created_at': datetime.utcnow()
        }
        
        result = profiles_collection.insert_one(new_profile)
        
        return jsonify({
            'message': 'Profile added successfully',
            'profile_id': str(result.inserted_id),
            'profile_name': profile_name,
            'emoji': random_emoji
        }), 201
        
    except Exception as e:
        print(f"Add profile error: {e}")
        return jsonify({'message': 'Server error'}), 500

@profile_bp.route('/rename-profile/<profile_id>', methods=['PUT'])
@jwt_required()
def rename_profile(profile_id):
    """Rename a profile"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        new_name = data.get('display_name')
        
        if not new_name:
            return jsonify({'message': 'New name required'}), 400
        
        result = profiles_collection.update_one(
            {
                '_id': ObjectId(profile_id),
                'user_id': ObjectId(user_id)
            },
            {'$set': {'display_name': new_name}}
        )
        
        if result.modified_count > 0:
            return jsonify({'message': 'Profile renamed successfully'}), 200
        else:
            return jsonify({'message': 'Profile not found'}), 404
            
    except Exception as e:
        print(f"Rename profile error: {e}")
        return jsonify({'message': 'Server error'}), 500

@profile_bp.route('/delete-profile/<profile_id>', methods=['DELETE'])
@jwt_required()
def delete_profile(profile_id):
    """Delete a profile"""
    try:
        user_id = get_jwt_identity()
        
        # Check if this is the last profile
        count = profiles_collection.count_documents({'user_id': ObjectId(user_id)})
        if count <= 1:
            return jsonify({'message': 'Cannot delete the last profile'}), 400
        
        result = profiles_collection.delete_one({
            '_id': ObjectId(profile_id),
            'user_id': ObjectId(user_id)
        })
        
        if result.deleted_count > 0:
            # Also delete all pantry items for this profile
            pantry_items_collection.delete_many({
                'user_id': ObjectId(user_id),
                'profile_id': profile_id
            })
            
            return jsonify({'message': 'Profile deleted successfully'}), 200
        else:
            return jsonify({'message': 'Profile not found'}), 404
            
    except Exception as e:
        print(f"Delete profile error: {e}")
        return jsonify({'message': 'Server error'}), 500