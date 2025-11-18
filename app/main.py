# app/main.py
# app/main.py
from flask import Flask, request
from flask_cors import CORS
from app.routes import optimizer_routes, auth_routes, user_routes

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object('app.config.Config')
    
    # CORS configuration - more permissive for debugging
    CORS(app, 
         origins=[
             "http://localhost:3000",
             "http://localhost:5173",
             "https://lumberlogic-frontend.vercel.app"
         ],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization"],
         max_age=3600
    )
    
    # Register blueprints
    app.register_blueprint(optimizer_routes.bp)
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(user_routes.bp)
    
    # Health check endpoint
    @app.route("/health", methods=["GET"])
    def health():
        return {"status": "ok"}, 200
    
    # Add explicit OPTIONS handler for all routes
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173", 
            "https://lumberlogic-frontend.vercel.app"
        ]
        if origin in allowed_origins:
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)