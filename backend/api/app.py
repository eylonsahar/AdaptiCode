"""Flask application initialization."""
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from backend.config import Config

# Load environment variables from .env file
load_dotenv()


def create_app():
    """Create and configure Flask application."""
    # The app serves both the HTML pages and the JSON API.
    app = Flask(
        __name__,
        template_folder='../../templates',
        static_folder='../../static',
    )
    
    # Enable CORS for frontend communication
    CORS(app)
    
    # Configuration
    app.config['DEBUG'] = Config.FLASK_DEBUG
    
    # Register routes (HTML + API)
    from backend.api.routes import register_routes
    register_routes(app)
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )

