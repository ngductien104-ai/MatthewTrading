import test from 'node:test';
import assert from 'node:assert/strict';
import { ThirdEyesClient } from './thirdEyes.ts';

test('bearer stays in headers; signals and ack use the versioned contract', async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({url, options});
    return new Response(JSON.stringify({items: [], total: 0}), {status: 200});
  };
  try {
    const client = new ThirdEyesClient('http://localhost:8790', () => 'secret');
    assert.equal((await client.signals()).total, 0);
    await client.acknowledge('a/b');
    assert.equal(calls[1].options.method, 'POST');
    assert.match(calls[1].url, /a%2Fb\/ack$/);
    assert.equal(calls[0].options.headers.Authorization, 'Bearer secret');
    assert.ok(calls.every(c => !c.url.includes('secret')));
  } finally { globalThis.fetch = original; }
});

test('SSE handles split UTF-8 frames, ignores replayed IDs and supports abort', async () => {
  const original = globalThis.fetch;
  const controller = new AbortController();
  const bytes = new TextEncoder().encode('id: 1\nevent: signal\ndata: {}\n\nid: 2\nevent: signal\ndata: {"text":"Vĩ mô"}\n\n');
  globalThis.fetch = async () => new Response(new ReadableStream({
    start(c) { for (let i=0; i<bytes.length; i+=7) c.enqueue(bytes.slice(i,i+7)); c.close(); },
  }));
  const events = [];
  try {
    const client = new ThirdEyesClient('http://localhost:8790', () => 'secret');
    await client.events(1, e => { events.push(e); controller.abort(); }, controller.signal);
    assert.deepEqual(events, [{id: 2, event: 'signal', data: {text: 'Vĩ mô'}}]);
  } finally { globalThis.fetch = original; }
});
