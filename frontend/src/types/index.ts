// ── Auth ──────────────────────────────────────────────────────────────────────

export type UserRole = 'admin' | 'analyst' | 'viewer'

export interface User {
  id: string
  email: string
  full_name: string | null
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

// ── Marketplace ───────────────────────────────────────────────────────────────

export type Marketplace = 'shopee' | 'jdcom'

// ── Seller ────────────────────────────────────────────────────────────────────

export interface Seller {
  id: string
  external_id: string
  marketplace: Marketplace
  name: string
  profile_url: string | null
  score: number | null
  reputation: number | null
  total_products: number
  is_active: boolean
  created_at: string
  updated_at: string
}

// ── Product ───────────────────────────────────────────────────────────────────

export interface Product {
  id: string
  external_id: string
  marketplace: Marketplace
  sku: string | null
  url: string | null
  title: string
  price: number | null
  original_price: number | null
  currency: string
  rating: number | null
  reviews_count: number
  stock_quantity: number | null
  is_available: boolean
  seller_id: string | null
  last_scraped_at: string | null
  created_at: string
  updated_at: string
}

// ── Price History ─────────────────────────────────────────────────────────────

export interface PricePoint {
  price: number
  scraped_at: string
  price_changed: boolean
  price_diff: number | null
}

export interface PriceAnalytics {
  product_id: string
  period_days: number
  data_points: number
  min_price: number | null
  max_price: number | null
  avg_price: number | null
  current_price: number | null
  history: PricePoint[]
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface SellerAnalyticsRow {
  id: string
  name: string
  marketplace: Marketplace
  score: number | null
  total_products: number
  tracked_products: number
}

export interface SellerAnalytics {
  sellers: SellerAnalyticsRow[]
}

// ── Pagination ────────────────────────────────────────────────────────────────

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

// ── Health / Jobs ─────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok' | 'degraded'
  environment: string
  version: string
  services: Record<string, string>
}

export interface JobsResponse {
  active:    Record<string, unknown[]>
  reserved:  Record<string, unknown[]>
  scheduled: Record<string, unknown[]>
  error?: string
}

// ── Scraping control ──────────────────────────────────────────────────────────

export interface TriggerResponse {
  task_id: string
  status: string
  detail: string
}

export interface TaskStatus {
  task_id: string
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'REVOKED'
  result: unknown | null
  traceback: string | null
}

// ── UI helpers ────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string
}

export type LoadingState = 'idle' | 'loading' | 'success' | 'error'
