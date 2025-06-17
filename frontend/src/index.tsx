import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import ConsoleApp from './ConsoleApp';
import DemoApp from './DemoApp';

// Get the base path from environment variable set during build
const basePath = process.env.REACT_APP_BASE_PATH || '';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <Router basename={basePath}>
      <Routes>
        <Route path="/console/*" element={<ConsoleApp />} />
        <Route path="/demo/*" element={<DemoApp />} />
        <Route path="/" element={<Navigate to="/console" replace />} />
      </Routes>
    </Router>
  </React.StrictMode>
);