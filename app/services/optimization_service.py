# app/services/optimization_service.py
from datetime import datetime
from app.database.supabase_client import supabase
import json

class OptimizationService:
    def save_optimization(self, user_id, cuts, boards, result, project_name=None):
        """Save optimization to user's history"""
        try:
            optimization_data = {
                "user_id": user_id,
                "project_name": project_name,
                "cuts": json.dumps(cuts),
                "boards": json.dumps(boards),
                "result": json.dumps(result),
                "total_cost": result.get('total_cost'),
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = supabase.table("optimizations").insert(optimization_data).execute()
            return response.data[0] if response.data else None
            
        except Exception as e:
            print(f"Error saving optimization: {str(e)}")
            return None
    
    def get_user_history(self, user_id, page=1, limit=20):
        """Get user's optimization history with pagination"""
        try:
            offset = (page - 1) * limit
            
            # Get total count
            count_response = supabase.table("optimizations") \
                .select("*", count="exact") \
                .eq("user_id", user_id) \
                .execute()
            
            total_count = count_response.count if hasattr(count_response, 'count') else 0
            
            # Get paginated results
            response = supabase.table("optimizations") \
                .select("id, project_name, total_cost, created_at") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()
            
            return {
                "optimizations": response.data,
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": (total_count + limit - 1) // limit
            }
            
        except Exception as e:
            print(f"Error getting history: {str(e)}")
            raise
    
    def get_optimization(self, optimization_id, user_id):
        """Get specific optimization by ID"""
        try:
            response = supabase.table("optimizations") \
                .select("*") \
                .eq("id", optimization_id) \
                .eq("user_id", user_id) \
                .execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            optimization = response.data[0]
            
            # Parse JSON fields
            optimization['cuts'] = json.loads(optimization['cuts'])
            optimization['boards'] = json.loads(optimization['boards'])
            optimization['result'] = json.loads(optimization['result'])
            
            return optimization
            
        except Exception as e:
            print(f"Error getting optimization: {str(e)}")
            raise
    
    def delete_optimization(self, optimization_id, user_id):
        """Delete optimization from history"""
        try:
            response = supabase.table("optimizations") \
                .delete() \
                .eq("id", optimization_id) \
                .eq("user_id", user_id) \
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error deleting optimization: {str(e)}")
            return False