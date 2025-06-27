# auth_app.py - Microservizio dedicato per Autenticazione
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from datetime import datetime

# Carica variabili ambiente
load_dotenv()

# Crea app Flask
app = Flask(__name__)

# Configurazione CORS - stesso del video service + porta 8001
CORS(app, origins=[
    'http://localhost:3000',
    'http://localhost:5173', 
    'https://new-maat.vercel.app',
    'http://localhost:8000'  # Permetti chiamate dal video service
])

# Configurazione Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auth_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'maat-auth-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Token non scadono per semplicità

# Inizializza estensioni
from models import db
db.init_app(app)

jwt = JWTManager(app)

# Importa e registra blueprint autenticazione
from auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# Endpoint di health check specifico per auth service
@app.route('/api/auth/health', methods=['GET'])
def auth_health():
    """Health check per servizio autenticazione"""
    try:
        # Test connessione database
        with app.app_context():
            from models import User
            user_count = User.query.count()
        
        return jsonify({
            'service': 'MAAT Authentication Service',
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'users_count': user_count,
            'jwt_configured': bool(app.config['JWT_SECRET_KEY']),
            'port': 8001
        })
    except Exception as e:
        return jsonify({
            'service': 'MAAT Authentication Service',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Endpoint root per info servizio
@app.route('/', methods=['GET'])
@app.route('/api/auth', methods=['GET'])
def auth_info():
    """Informazioni servizio autenticazione"""
    return jsonify({
        'service': 'MAAT Authentication Service',
        'version': '1.0.0',
        'description': 'Microservizio dedicato per autenticazione utenti MAAT',
        'endpoints': [
            'POST /api/auth/register',
            'POST /api/auth/login', 
            'POST /api/auth/google-login',
            'GET /api/auth/verify-token',
            'POST /api/auth/logout',
            'POST /api/auth/request-password-reset',
            'POST /api/auth/reset-password',
            'GET /api/auth/health'
        ],
        'cors_enabled': True,
        'jwt_enabled': True,
        'database': 'sqlite',
        'port': 8001
    })

# Gestione errori JWT
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'success': False,
        'error': 'Token scaduto'
    }), 401

@jwt.invalid_token_loader  
def invalid_token_callback(error):
    return jsonify({
        'success': False,
        'error': 'Token non valido'
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({
        'success': False,  
        'error': 'Token mancante'
    }), 401

# Inizializza database al primo avvio
def init_database():
    """Inizializza database se non esiste"""
    try:
        with app.app_context():
            db.create_all()
            print("✅ Database autenticazione inizializzato")
            
            # Verifica tabelle create
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📊 Tabelle database: {', '.join(tables)}")
            
    except Exception as e:
        print(f"❌ Errore inizializzazione database: {e}")
        raise

if __name__ == '__main__':
    print("🚀 Avviando MAAT Authentication Service...")
    print("🔐 Microservizio dedicato per autenticazione")
    print("📡 Porta: 8001")
    print("🗄️ Database: auth_database.db")
    
    # Inizializza database
    init_database()
    
    # Avvia servizio
    app.run(
        debug=True, 
        host='0.0.0.0', 
        port=8001,
        threaded=True
    )
