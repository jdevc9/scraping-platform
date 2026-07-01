import React, { createContext, useContext, useState, useCallback } from 'react'
import { authApi } from '@/api'
import type { UserRole } from '@/types'

interface AuthUser {
  id: string
  email: string
  role: UserRole
}

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isRole: (...roles: UserRole[]) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

function parseToken(token: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return {
      id: payload.sub,
      email: payload.email ?? '',
      role: (payload.role as UserRole) ?? 'viewer',
    }
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'))
  const [user, setUser] = useState<AuthUser | null>(() => {
    const t = localStorage.getItem('access_token')
    return t ? parseToken(t) : null
  })
  const [isLoading, setIsLoading] = useState(false)

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const { access_token } = await authApi.login(email, password)
      localStorage.setItem('access_token', access_token)
      setToken(access_token)
      setUser(parseToken(access_token))
    } finally {
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    setToken(null)
    setUser(null)
    window.location.href = '/login'
  }, [])

  const isRole = useCallback((...roles: UserRole[]) => {
    return user ? roles.includes(user.role) : false
  }, [user])

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout, isRole }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
