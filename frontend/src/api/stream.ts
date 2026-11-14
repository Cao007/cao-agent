import type { components } from './schema'

export type RunEvent =
  | { type: 'start'; run_id: string }
  | { type: 'token'; content: string }
  | { type: 'progress'; message: string }
  | { type: 'paused'; review: components['schemas']['Extraction'] }
  | { type: 'result'; result: components['schemas']['Extraction'] | null }
  | { type: 'done' }
  | { type: 'error'; message: string; run_id: string }

/**
 * 自有 FastAPI 的 POST SSE 边界。终止前断连算失败，取消通过 AbortSignal 传播。
 */
export async function streamRun(
  path: string, body: unknown, csrf: string, signal: AbortSignal,
  onEvent: (event: RunEvent) => void,
): Promise<void> {
  const response = await fetch(path, {
    method: 'POST', credentials: 'same-origin', signal,
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as { detail?: unknown }
    throw new Error(typeof error.detail === 'string' ? error.detail : '无法开始运行，请稍后重试。')
  }
  if (!response.body) throw new Error('浏览器无法读取流式响应。')
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  let isDone = false
  function consumeFrame(frame: string) {
    const data = frame.split('\n').filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart()).join('\n')
    if (!data) return
    const event = JSON.parse(data) as RunEvent
    if (event.type === 'error') throw new Error(event.message)
    onEvent(event)
    if (event.type === 'done' || event.type === 'paused') isDone = true
  }
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += value
      // 后端使用 LF；兼容标准 SSE 的 CRLF，包括跨分片 CR/LF。
      buffer = buffer.replace(/\r\n/g, '\n')
      let end: number
      while ((end = buffer.indexOf('\n\n')) >= 0) {
        consumeFrame(buffer.slice(0, end))
        buffer = buffer.slice(end + 2)
      }
    }
    if (buffer.trim()) consumeFrame(buffer)
    if (!isDone) throw new Error('连接中断，运行未完成，请重新加载记录后重试。')
  } finally {
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}
