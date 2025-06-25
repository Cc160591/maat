// AuthContext.jsx - Gestione globale autenticazione
import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

// Crea il Context
const AuthContext = createContext();

// Hook personalizzato per usare l'auth
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve essere usato dentro AuthProvider');
  }
  return context;
};

// Provider del Context
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // API Base URL - IMPORTANTE: deve corrispondere al backend
  const API_BASE = 'http://localhost:8000'; // Backend locale
  // const API_BASE = 'https://maat-production.up.railway.app'; // Se usi Railway

  // Configurazione axios con token
  const setupAxiosInterceptors = (authToken) => {
    if (authToken) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  };

  // Verifica token al caricamento dell'app
  useEffect(() => {
    const initAuth = async () => {
      try {
        const savedToken = localStorage.getItem('auth_token');
        const savedUser = localStorage.getItem('auth_user');

        if (savedToken && savedUser) {
          setupAxiosInterceptors(savedToken);
          
          // Verifica che il token sia ancora valido
          const response = await axios.get(`${API_BASE}/api/auth/verify-token`);
          
          if (response.data.success) {
            setToken(savedToken);
            setUser(JSON.parse(savedUser));
          } else {
            // Token non valido, rimuovi tutto
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');
          }
        }
      } catch (error) {
        console.error('Errore verifica token:', error);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // Funzione di login
  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API_BASE}/api/auth/login`, {
        email: email.trim().toLowerCase(),
        password
      });

      if (response.data.success) {
        const { user, access_token } = response.data;
        
        // Salva in localStorage
        localStorage.setItem('auth_token', access_token);
        localStorage.setItem('auth_user', JSON.stringify(user));
        
        // Aggiorna stato
        setToken(access_token);
        setUser(user);
        setupAxiosInterceptors(access_token);

        return { success: true, user };
      } else {
        return { success: false, error: response.data.error };
      }
    } catch (error) {
      console.error('Errore login:', error);
      return { 
        success: false, 
        error: error.response?.data?.error || 'Errore di connessione' 
      };
    }
  };

  // Funzione di registrazione
  const register = async (email, username, password) => {
    try {
      const response = await axios.post(`${API_BASE}/api/auth/register`, {
        email: email.trim().toLowerCase(),
        username: username.trim(),
        password
      });

      if (response.data.success) {
        const { user, access_token } = response.data;
        
        // Salva in localStorage
        localStorage.setItem('auth_token', access_token);
        localStorage.setItem('auth_user', JSON.stringify(user));
        
        // Aggiorna stato
        setToken(access_token);
        setUser(user);
        setupAxiosInterceptors(access_token);

        return { success: true, user };
      } else {
        return { success: false, error: response.data.error };
      }
    } catch (error) {
      console.error('Errore registrazione:', error);
      return { 
        success: false, 
        error: error.response?.data?.error || 'Errore di connessione' 
      };
    }
  };

  // Funzione di logout
  const logout = async () => {
    try {
      if (token) {
        await axios.post(`${API_BASE}/api/auth/logout`);
      }
    } catch (error) {
      console.error('Errore logout:', error);
    } finally {
      // Rimuovi tutto comunque
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      setToken(null);
      setUser(null);
      setupAxiosInterceptors(null);
    }
  };

  // Login con Google (placeholder per ora)
  const googleLogin = async (googleToken) => {
    try {
      const response = await axios.post(`${API_BASE}/api/auth/google-login`, {
        google_token: googleToken
      });

      if (response.data.success) {
        const { user, access_token } = response.data;
        
        localStorage.setItem('auth_token', access_token);
        localStorage.setItem('auth_user', JSON.stringify(user));
        
        setToken(access_token);
        setUser(user);
        setupAxiosInterceptors(access_token);

        return { success: true, user };
      } else {
        return { success: false, error: response.data.error };
      }
    } catch (error) {
      console.error('Errore Google login:', error);
      return { 
        success: false, 
        error: error.response?.data?.error || 'Errore Google login' 
      };
    }
  };

  // Reset password
  const requestPasswordReset = async (email) => {
    try {
      const response = await axios.post(`${API_BASE}/api/auth/request-password-reset`, {
        email: email.trim().toLowerCase()
      });

      return { 
        success: response.data.success, 
        message: response.data.message 
      };
    } catch (error) {
      console.error('Errore reset password:', error);
      return { 
        success: false, 
        error: error.response?.data?.error || 'Errore richiesta reset' 
      };
    }
  };

  // Valori del context
  const value = {
    // Stato
    user,
    token,
    loading,
    isAuthenticated: !!token && !!user,
    
    // Funzioni
    login,
    register,
    logout,
    googleLogin,
    requestPasswordReset
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
