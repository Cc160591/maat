# auth.py - Endpoint di autenticazione
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User, UserSession, PasswordReset
from datetime import datetime, timedelta
import secrets
import re
import requests

# Blueprint per organizzare gli endpoint
auth_bp = Blueprint('auth', __name__)

def is_valid_email(email):
    """Valida formato email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_password(password):
    """Valida password (minimo 8 caratteri, almeno 1 lettera e 1 numero)"""
    if len(password) < 8:
        return False, "Password deve essere di almeno 8 caratteri"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password deve contenere almeno una lettera"
    if not re.search(r'[0-9]', password):
        return False, "Password deve contenere almeno un numero"
    return True, "OK"

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registrazione nuovo utente"""
    try:
        data = request.get_json()
        
        email = data.get('email', '').strip().lower()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validazioni
        if not email or not username or not password:
            return jsonify({
                'success': False,
                'error': 'Email, username e password sono richiesti'
            }), 400
        
        if not is_valid_email(email):
            return jsonify({
                'success': False,
                'error': 'Formato email non valido'
            }), 400
        
        valid_password, password_msg = is_valid_password(password)
        if not valid_password:
            return jsonify({
                'success': False,
                'error': password_msg
            }), 400
        
        # Controlla se utente esiste già
        if User.query.filter_by(email=email).first():
            return jsonify({
                'success': False,
                'error': 'Email già registrata'
            }), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({
                'success': False,
                'error': 'Username già in uso'
            }), 400
        
        # Crea nuovo utente
        user = User(
            email=email,
            username=username,
            is_google_user=False
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Crea token di accesso
        access_token = create_access_token(identity=user.user_id)
        
        # Aggiorna ultimo login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Registrazione completata',
            'user': user.to_dict(),
            'access_token': access_token
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore durante registrazione: {str(e)}'
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login utente"""
    try:
        data = request.get_json()
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email e password sono richiesti'
            }), 400
        
        # Trova utente
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({
                'success': False,
                'error': 'Credenziali non valide'
            }), 401
        
        if not user.is_active:
            return jsonify({
                'success': False,
                'error': 'Account disattivato'
            }), 401
        
        # Crea token di accesso
        access_token = create_access_token(identity=user.user_id)
        
        # Aggiorna ultimo login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Login effettuato',
            'user': user.to_dict(),
            'access_token': access_token
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore durante login: {str(e)}'
        }), 500

@auth_bp.route('/google-login', methods=['POST'])
def google_login():
    """Login con Google"""
    try:
        data = request.get_json()
        google_token = data.get('google_token')
        
        if not google_token:
            return jsonify({
                'success': False,
                'error': 'Token Google richiesto'
            }), 400
        
        # Verifica token con Google
        google_api_url = f'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={google_token}'
        response = requests.get(google_api_url)
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': 'Token Google non valido'
            }), 401
        
        google_data = response.json()
        google_id = google_data.get('user_id')
        email = google_data.get('email')
        
        if not google_id or not email:
            return jsonify({
                'success': False,
                'error': 'Dati Google incompleti'
            }), 400
        
        # Cerca utente esistente
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            # Cerca per email
            user = User.query.filter_by(email=email.lower()).first()
            
            if user:
                # Collega account Google a utente esistente
                user.google_id = google_id
                user.is_google_user = True
            else:
                # Crea nuovo utente Google
                username = email.split('@')[0]  # Username dal email
                
                # Assicurati che username sia unico
                counter = 1
                original_username = username
                while User.query.filter_by(username=username).first():
                    username = f"{original_username}{counter}"
                    counter += 1
                
                user = User(
                    email=email.lower(),
                    username=username,
                    google_id=google_id,
                    is_google_user=True
                )
                db.session.add(user)
        
        # Aggiorna ultimo login
        user.last_login = datetime.utcnow()
        user.is_active = True
        db.session.commit()
        
        # Crea token di accesso
        access_token = create_access_token(identity=user.user_id)
        
        return jsonify({
            'success': True,
            'message': 'Login Google effettuato',
            'user': user.to_dict(),
            'access_token': access_token
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore durante login Google: {str(e)}'
        }), 500

@auth_bp.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    """Verifica validità token"""
    try:
        user_id = get_jwt_identity()
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user or not user.is_active:
            return jsonify({
                'success': False,
                'error': 'Token non valido'
            }), 401
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore verifica token: {str(e)}'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout utente (per ora solo conferma, JWT è stateless)"""
    try:
        user_id = get_jwt_identity()
        
        return jsonify({
            'success': True,
            'message': 'Logout effettuato'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Errore durante logout: {str(e)}'
        }), 500

@auth_bp.route('/request-password-reset', methods=['POST'])
def request_password_reset():
    """Richiedi reset password"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({
                'success': False,
                'error': 'Email richiesta'
            }), 400
        
        user = User.query.filter_by(email=email).first()
        
        # Per sicurezza, sempre risposta positiva anche se email non esiste
        if user and not user.is_google_user:
            # Crea token reset
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            reset_request = PasswordReset(
                user_id=user.user_id,
                reset_token=reset_token,
                expires_at=expires_at
            )
            
            db.session.add(reset_request)
            db.session.commit()
            
            # TODO: Qui inviare email con il link di reset
            # Per ora solo loggiamo il token
            print(f"🔑 Reset token per {email}: {reset_token}")
        
        return jsonify({
            'success': True,
            'message': 'Se l\'email esiste, riceverai le istruzioni per il reset'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore richiesta reset: {str(e)}'
        }), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password con token"""
    try:
        data = request.get_json()
        reset_token = data.get('reset_token')
        new_password = data.get('new_password')
        
        if not reset_token or not new_password:
            return jsonify({
                'success': False,
                'error': 'Token e nuova password richiesti'
            }), 400
        
        # Valida password
        valid_password, password_msg = is_valid_password(new_password)
        if not valid_password:
            return jsonify({
                'success': False,
                'error': password_msg
            }), 400
        
        # Trova reset token valido
        reset_request = PasswordReset.query.filter_by(
            reset_token=reset_token,
            is_used=False
        ).first()
        
        if not reset_request or reset_request.expires_at < datetime.utcnow():
            return jsonify({
                'success': False,
                'error': 'Token non valido o scaduto'
            }), 400
        
        # Aggiorna password
        user = User.query.filter_by(user_id=reset_request.user_id).first()
        if user:
            user.set_password(new_password)
            reset_request.is_used = True
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Password aggiornata con successo'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Utente non trovato'
            }), 404
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore reset password: {str(e)}'
        }), 500
