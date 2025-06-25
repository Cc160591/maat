// AuthLayout.jsx - Layout coerente con l'app principale
import React from 'react';
import { Video, Zap } from 'lucide-react';

const AuthLayout = ({ children, title, subtitle }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-100 to-cyan-100 flex items-center justify-center p-4">
      
      <div className="w-full max-w-md">
        {/* Logo e Header - Stesso stile dell'app */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center mx-auto mb-4 shadow-lg">
            <Video className="text-white" size={32} />
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 mb-2 flex items-center justify-center gap-2">
            MAAT
            <Zap className="w-5 h-5 text-blue-500" />
          </h1>
          
          <p className="text-gray-600 text-sm">
            AI-Powered Stream Highlights
          </p>
        </div>

        {/* Card Principale - Stesso stile dell'app */}
        <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 p-8">
          {/* Titolo Pagina */}
          <div className="text-center mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {title}
            </h2>
            {subtitle && (
              <p className="text-gray-600 text-sm">
                {subtitle}
              </p>
            )}
          </div>

          {/* Contenuto (Form) */}
          {children}
        </div>

        {/* Footer */}
        <div className="text-center mt-6">
          <p className="text-gray-500 text-xs">
            © 2025 MAAT AI - Advanced Video Processing
          </p>
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
