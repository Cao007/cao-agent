import createClient from 'openapi-fetch'
import type { paths, components } from './schema'

export type UserInfo = components['schemas']['CurrentUser']
export type ThreadInfo = components['schemas']['ThreadInfo']
export type ThreadDetail = components['schemas']['ThreadDetail']
export type AnalysisInfo = components['schemas']['AnalysisInfo']
export type Extraction = components['schemas']['Extraction']

let csrfToken = ''
export const setCsrfToken = (token: string) => { csrfToken = token }
export const getCsrfToken = () => csrfToken
export const client = createClient<paths>({ credentials: 'same-origin' })
client.use({
  onRequest({ request }) {
    if (!['GET', 'HEAD'].includes(request.method)) request.headers.set('X-CSRF-Token', csrfToken)
    return request
  },
})

export function unwrap<T>(response: { data?: T; error?: unknown }): T {
  if (response.error || response.data === undefined) {
    const detail = (response.error as { detail?: unknown })?.detail
    throw new Error(typeof detail === 'string' ? detail : '请求失败，请检查输入或稍后重试。')
  }
  return response.data
}
