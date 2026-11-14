import { ref } from 'vue'
import { defineStore } from 'pinia'
import { client, setCsrfToken, unwrap, type UserInfo } from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const isLoaded = ref(false)
  function setUser(value: UserInfo | null) {
    user.value = value
    setCsrfToken(value?.csrf_token ?? '')
    isLoaded.value = true
  }
  async function load() {
    const response = await client.GET('/api/auth/me')
    if (response.response.status === 401) setUser(null)
    else setUser(unwrap(response))
  }
  async function login(username: string, password: string, isRegister: boolean) {
    const response = await client.POST(isRegister ? '/api/auth/register' : '/api/auth/login', {
      body: { username, password },
    })
    setUser(unwrap(response))
  }
  async function logout() {
    const response = await client.POST('/api/auth/logout')
    if (!response.response.ok) throw new Error('退出失败，请稍后重试。')
    setUser(null)
  }
  return { user, isLoaded, load, login, logout }
})
