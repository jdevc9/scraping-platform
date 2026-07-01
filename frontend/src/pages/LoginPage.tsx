import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Button, Input } from '@/components/ui'

export default function LoginPage() {
  const { login, isLoading } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('Invalid email or password. Try admin@platform.local / admin123')
    }
  }

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm animate-fade-in">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 mb-4">
            <Zap className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">Scraping Platform</h1>
          <p className="text-sm text-slate-400 mt-1">Sign in to your account</p>
        </div>

        {/* Form */}
        <div className="bg-surface-900 rounded-2xl border border-surface-800 p-6 space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              id="email"
              label="Email"
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="admin@platform.local"
              required
            />
            <Input
              id="password"
              label="Password"
              type="password"
              value={password}
              onChange={setPassword}
              placeholder="••••••••"
              required
            />

            {error && (
              <p className="text-xs text-red-400 bg-red-900/30 border border-red-800 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <Button type="submit" isLoading={isLoading} className="w-full justify-center">
              Sign in
            </Button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">
          Senior Automation & Scraping Platform v1.0
        </p>
      </div>
    </div>
  )
}
