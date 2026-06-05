import React, { createContext, useContext, useState } from 'react';

// Change this to your Mac's local IP so your phone can reach the Flask server
// Run: ipconfig getifaddr en0   in terminal to find your IP
export const API_BASE = 'http://192.168.1.226:5001';

const AppContext = createContext();

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);

  async function apiCall(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
      credentials: 'include',
    });
    return res.json();
  }

  async function login(username, password) {
    const data = await apiCall('/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    if (data.ok) {
      const me = await apiCall('/api/me');
      setUser(me);
    }
    return data;
  }

  async function register(username, password) {
    const data = await apiCall('/register', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    if (data.ok) {
      const me = await apiCall('/api/me');
      setUser(me);
    }
    return data;
  }

  async function refreshUser() {
    const me = await apiCall('/api/me');
    if (!me.error) setUser(me);
  }

  function logout() {
    setUser(null);
  }

  return (
    <AppContext.Provider value={{ user, login, register, logout, refreshUser, apiCall }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  return useContext(AppContext);
}
