import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext.jsx';
import { App } from './App.jsx';
import { APP_NAME } from './config/brand.js';
import './styles.css';
// Browser title follows the replaceable brand setting.
document.title = APP_NAME;
createRoot(document.getElementById('root')).render(<React.StrictMode><BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter></React.StrictMode>);
