import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './theme/tailwind.css';
import { ControlProvider } from './context/ControlProvider';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ControlProvider>
      <App />
    </ControlProvider>
  </React.StrictMode>
);
