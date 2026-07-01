import axios, { type AxiosInstance } from 'axios'
import type {
  TokenResponse, Product, Paginated, Seller,
  PriceAnalytics, SellerAnalytics, HealthResponse, JobsResponse,
  TriggerResponse, TaskStatus,
} from '@/types'

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api/v1'

function createClient(): AxiosInstance {
  const client = axios.create({ baseURL: BASE_URL, timeout: 15_000 })

  client.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })

  client.interceptors.response.use(
    (res) => res,
    (err) => {
      if (err.response?.status === 401) {
        localStorage.removeItem('access_token')
        window.location.href = '/login'
      }
      return Promise.reject(err)
    },
  )

  return client
}

const http = createClient()

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const form = new URLSearchParams({ username: email, password })
    const res = await http.post<TokenResponse>('/auth/token', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return res.data
  },
}

// ── Products ──────────────────────────────────────────────────────────────────

export const productsApi = {
  list: async (params: {
    page?: number
    page_size?: number
    marketplace?: string
    search?: string
    is_available?: boolean
  } = {}): Promise<Paginated<Product>> => {
    const res = await http.get<Paginated<Product>>('/products', { params })
    return res.data
  },

  get: async (id: string): Promise<Product> => {
    const res = await http.get<Product>(`/products/${id}`)
    return res.data
  },

  create: async (payload: { external_id: string; marketplace: string; title: string; url?: string }): Promise<Product> => {
    const res = await http.post<Product>('/products', payload)
    return res.data
  },
}

// ── Sellers ───────────────────────────────────────────────────────────────────

export const sellersApi = {
  list: async (params: { page?: number; page_size?: number; marketplace?: string } = {}): Promise<Paginated<Seller>> => {
    const res = await http.get<Paginated<Seller>>('/sellers', { params })
    return res.data
  },

  get: async (id: string): Promise<Seller> => {
    const res = await http.get<Seller>(`/sellers/${id}`)
    return res.data
  },
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export const analyticsApi = {
  prices: async (product_id: string, days = 30): Promise<PriceAnalytics> => {
    const res = await http.get<PriceAnalytics>('/analytics/prices', { params: { product_id, days } })
    return res.data
  },

  sellers: async (params: { marketplace?: string; limit?: number } = {}): Promise<SellerAnalytics> => {
    const res = await http.get<SellerAnalytics>('/analytics/sellers', { params })
    return res.data
  },
}

// ── Monitoring ────────────────────────────────────────────────────────────────

export const monitoringApi = {
  health: async (): Promise<HealthResponse> => {
    const res = await http.get<HealthResponse>('/health')
    return res.data
  },

  jobs: async (): Promise<JobsResponse> => {
    const res = await http.get<JobsResponse>('/jobs')
    return res.data
  },
}

// ── Scraping control ──────────────────────────────────────────────────────────

export const scrapingApi = {
  triggerProduct: async (product_id: string): Promise<TriggerResponse> => {
    const res = await http.post<TriggerResponse>('/scraping/trigger/product', { product_id })
    return res.data
  },

  triggerMarketplace: async (marketplace: string): Promise<TriggerResponse> => {
    const res = await http.post<TriggerResponse>(`/scraping/trigger/marketplace?marketplace=${marketplace}`)
    return res.data
  },

  search: async (marketplace: string, keyword: string, max_results = 20): Promise<TriggerResponse> => {
    const res = await http.post<TriggerResponse>('/scraping/search', { marketplace, keyword, max_results })
    return res.data
  },

  taskStatus: async (task_id: string): Promise<TaskStatus> => {
    const res = await http.get<TaskStatus>(`/scraping/task/${task_id}`)
    return res.data
  },

  marketplaces: async (): Promise<{ marketplaces: string[] }> => {
    const res = await http.get<{ marketplaces: string[] }>('/scraping/marketplaces')
    return res.data
  },
}

export default http
