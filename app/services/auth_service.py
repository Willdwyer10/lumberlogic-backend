# app/services/auth_service.py
import os
import jwt
import requests
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.database.supabase_client import supabase
from app.config import Config

class AuthService:
    def __init__(self):
        self.google_client_id = Config.GOOGLE_CLIENT_ID
        self.google_client_secret = Config.GOOGLE_CLIENT_SECRET
        self.frontend_url = Config.FRONTEND_URL
        
    def get_google_authorization_url(self):
        """Generate Google OAuth authorization URL"""
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        
        # Get the backend URL from environment or construct it
        backend_url = os.getenv('BACKEND_URL', 'http://localhost:5000')
        # Remove trailing slash if present
        backend_url = backend_url.rstrip('/')
        redirect_uri = f"{backend_url}/auth/google/callback"
        
        params = {
            "client_id": self.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    def handle_google_callback(self, code):
        """Exchange authorization code for tokens and create/update user"""
        try:
            # Exchange code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            backend_url = os.getenv('BACKEND_URL', 'http://localhost:5000')
            # Remove trailing slash if present
            backend_url = backend_url.rstrip('/')
            
            data = {
                "code": code,
                "client_id": self.google_client_id,
                "client_secret": self.google_client_secret,
                "redirect_uri": f"{backend_url}/auth/google/callback",
                "grant_type": "authorization_code"
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            tokens = response.json()
            
            # Verify and decode ID token
            id_info = id_token.verify_oauth2_token(
                tokens['id_token'],
                google_requests.Request(),
                self.google_client_id
            )
            
            # Extract user information
            google_id = id_info['sub']
            email = id_info['email']
            name = id_info.get('name', '')
            picture = id_info.get('picture', '')
            
            # Create or update user in database
            user = self._create_or_update_user(google_id, email, name, picture)
            
            # Generate JWT tokens
            access_token = self._generate_access_token(user)
            refresh_token = self._generate_refresh_token(user)
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user['id'],
                    "email": user['email'],
                    "name": user['name'],
                    "picture": user.get('picture')
                }
            }
            
        except Exception as e:
            print(f"Error in Google callback: {str(e)}")
            return None
    
    def _create_or_update_user(self, google_id, email, name, picture):
        """Create new user or update existing user"""
        try:
            # Check if user exists
            response = supabase.table("users").select("*").eq("google_id", google_id).execute()
            
            if response.data and len(response.data) > 0:
                # Update existing user
                user = response.data[0]
                update_data = {
                    "name": name,
                    "picture": picture,
                    "last_login": datetime.utcnow().isoformat()
                }
                
                response = supabase.table("users").update(update_data).eq("id", user['id']).execute()
                return response.data[0]
            else:
                # Create new user
                new_user = {
                    "google_id": google_id,
                    "email": email,
                    "name": name,
                    "picture": picture,
                    "created_at": datetime.utcnow().isoformat(),
                    "last_login": datetime.utcnow().isoformat()
                }
                
                response = supabase.table("users").insert(new_user).execute()
                return response.data[0]
                
        except Exception as e:
            print(f"Error creating/updating user: {str(e)}")
            raise
    
    def _generate_access_token(self, user):
        """Generate JWT access token"""
        payload = {
            "user_id": user['id'],
            "email": user['email'],
            "exp": datetime.utcnow() + timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")
    
    def _generate_refresh_token(self, user):
        """Generate JWT refresh token"""
        payload = {
            "user_id": user['id'],
            "exp": datetime.utcnow() + timedelta(seconds=Config.JWT_REFRESH_TOKEN_EXPIRES),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")
    
    def refresh_access_token(self, refresh_token):
        """Generate new access token from refresh token"""
        try:
            payload = jwt.decode(refresh_token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            
            if payload.get('type') != 'refresh':
                return None
            
            user_id = payload.get('user_id')
            
            # Get user from database
            response = supabase.table("users").select("*").eq("id", user_id).execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            user = response.data[0]
            
            # Generate new access token
            access_token = self._generate_access_token(user)
            
            return {
                "access_token": access_token
            }
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def verify_access_token(self, token):
        """Verify JWT access token and return user"""
        try:
            payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            
            if payload.get('type') != 'access':
                return None
            
            user_id = payload.get('user_id')
            
            # Get user from database
            response = supabase.table("users").select("*").eq("id", user_id).execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            return response.data[0]
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None