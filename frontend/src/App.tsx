import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/hooks/useAuth'
import { AppLayout } from '@/components/layout/AppLayout'
import { LoadingOverlay } from '@/components/ui'

// Lazy load pages for better initial load performance
const LoginPage    = lazy(() => import('@/pages/LoginPage'))
const OverviewPage = lazy(() => import('@/pages/OverviewPage'))
const ProductsPage = lazy(() => import('@/pages/ProductsPage'))
const SellersPage  = lazy(() => import('@/pages/SellersPage'))
const AnalyticsPage = lazy(() => import('@/pages/AnalyticsPage'))
const JobsPage     = lazy(() => import('@/pages/JobsPage'))
const ScrapingPage = lazy(() => import('@/pages/ScrapingPage'))

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Suspense fallback={<LoadingOverlay />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route path="/"          element={<OverviewPage />} />
          <Route path="/products"  element={<ProductsPage />} />
          <Route path="/sellers"   element={<SellersPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/jobs"      element={<JobsPage />} />
          <Route path="/scraping"  element={<ScrapingPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}
