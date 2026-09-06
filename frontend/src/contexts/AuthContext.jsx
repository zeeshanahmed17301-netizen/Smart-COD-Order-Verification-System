/**
 * AuthContext — JWT authentication state management
 *
 * Provides: user, isAuthenticated, isLoading, login, signup, logout
 * Auto-loads user profile on mount if tokens exist.
 */
/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import authApi from '../api/auth';
import accountsApi from '../api/accounts';
import { setTokens, clearTokens, getAccessToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load user profile from stored tokens on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = getAccessToken();
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const { data } = await accountsApi.getProfile();
        setUser(data);
      } catch {
        clearTokens();
      } finally {
        setIsLoading(false);
      }
    };
    initAuth();
  }, []);

  const login = useCallback(async (email, password) => {
    const { data: tokens } = await authApi.login(email, password);
    setTokens(tokens.access, tokens.refresh);
    const { data: profile } = await accountsApi.getProfile();
    setUser(profile);
    return profile;
  }, []);

  const signup = useCallback(async (formData) => {
    await authApi.signup(formData);
    // Auto-login after signup
    const { data: tokens } = await authApi.login(formData.email, formData.password);
    setTokens(tokens.access, tokens.refresh);
    const { data: profile } = await accountsApi.getProfile();
    setUser(profile);
    return profile;
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const refreshProfile = useCallback(async () => {
    try {
      const { data } = await accountsApi.getProfile();
      setUser(data);
      return data;
    } catch {
      // Silent fail — profile refresh is best-effort
      return user;
    }
  }, [user]);

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    signup,
    logout,
    refreshProfile,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
