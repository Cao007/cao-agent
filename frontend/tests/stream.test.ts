import assert from 'node:assert/strict'
import test from 'node:test'
import { streamRun } from '../src/api/stream.ts'

test('流式协议保留分片中文，并区分完成、失败与断连', async () => {
  const originalFetch = globalThis.fetch
  const mockStream = (text: string) => {
    const bytes = new TextEncoder().encode(text)
    globalThis.fetch = async () => new Response(new ReadableStream({
      start(controller) {
        // 故意逐字节切分，覆盖中文 UTF-8 字符和 JSON 行跨分片的情况。
        for (const byte of bytes) controller.enqueue(Uint8Array.of(byte))
        controller.close()
      },
    }))
  }
  try {
    mockStream('data: {"type":"start","run_id":"1"}\r\n\r\ndata: {"type":"token","content":"你好\\n世界"}\r\n\r\ndata: {"type":"done"}\r\n\r\n')
    let answer = ''
    await streamRun('/api/test', {}, 'csrf',
      new AbortController().signal, (event) => {
        if (event.type === 'token') answer += event.content
      })
    assert.equal(answer, '你好\n世界')

    mockStream('data: {"type":"start","run_id":"1"}\n\n')
    await assert.rejects(streamRun('/api/test', {}, 'csrf', new AbortController().signal,
      () => undefined), /连接中断/)

    mockStream('data: {"type":"error","run_id":"1","message":"服务繁忙"}\n\n')
    await assert.rejects(streamRun('/api/test', {}, 'csrf', new AbortController().signal,
      () => undefined), /服务繁忙/)
    mockStream('data: {"type":"paused","review":{"title":"待审核","summary":"","key_points":[],"action_items":[]}}\n\n')
    let isPaused = false
    await streamRun('/api/test', {}, 'csrf', new AbortController().signal,
      (event) => { isPaused = event.type === 'paused' })
    assert.equal(isPaused, true)
  } finally {
    globalThis.fetch = originalFetch
  }
})
