# models.py - Modelli database per autenticazione
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import uuid

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    """Modello utente per autenticazione"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)  # Nullable per utenti Google
    is_google_user = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        """Imposta password criptata"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Verifica password"""
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Converte utente in dizionario (senza password)"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.email,
            'username': self.username,
            'is_google_user': self.is_google_user,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }

class UserSession(db.Model):
    """Modello per tracciare sessioni utente"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', backref=db.backref('sessions', lazy=True))

class PasswordReset(db.Model):
    """Modello per reset password"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=False)
    reset_token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('password_resets', lazy=True))
