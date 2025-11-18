# app/services/user_service.py
from app.database.supabase_client import supabase

class UserService:
    def get_user(self, user_id):
        """Get user by ID"""
        try:
            response = supabase.table("users").select("*").eq("id", user_id).execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            return response.data[0]
            
        except Exception as e:
            print(f"Error getting user: {str(e)}")
            raise
    
    def update_user(self, user_id, update_data):
        """Update user information"""
        try:
            response = supabase.table("users") \
                .update(update_data) \
                .eq("id", user_id) \
                .execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            return response.data[0]
            
        except Exception as e:
            print(f"Error updating user: {str(e)}")
            raise
    
    def delete_user(self, user_id):
        """Delete user account and all associated data"""
        try:
            # Delete user's optimizations first
            supabase.table("optimizations").delete().eq("user_id", user_id).execute()
            
            # Delete user
            response = supabase.table("users").delete().eq("id", user_id).execute()
            
            return True
            
        except Exception as e:
            print(f"Error deleting user: {str(e)}")
            return False