/** Fincept integration contract. Uses bearer headers; tokens never enter URLs. */
export interface ThirdEyesSignal {
  id: string; indicator: string; entity: string; domain: string; group: string;
  observed_at: string; detected_at: string; value: number; threshold: number;
  trend: string; pattern: string; rule_id: string; rule_version: string;
  snapshot: string; source: string; unit: string;
  tier: 'radar' | 'priority'; severity: 'watch' | 'elevated';
  direction: 'risk' | 'opportunity' | 'mixed'; state: 'new' | 'updated' | 'expired';
  ai_status: 'pending' | 'running' | 'completed' | 'failed';
  acknowledged_at: string | null; analysis: Record<string, unknown> | null;
  validation: Record<string, unknown> | null; confirmation_ids: string[];
  limitations: string[]; portfolio: Record<string, unknown>;
}

export interface ThirdEyesEvent { id: number; event: string; data: unknown }

export class ThirdEyesClient {
  private base: string;
  private token: () => string;
  constructor(base: string, token: () => string) { this.base = base; this.token = token; }

  async request<T>(path: string, method = 'GET'): Promise<T> {
    const response = await fetch(`${this.base}/third-eyes/v1${path}`, {
      method, headers: { Authorization: `Bearer ${this.token()}` },
    });
    if (!response.ok) throw new Error(`Third Eyes HTTP ${response.status}`);
    return response.json() as Promise<T>;
  }

  signals() { return this.request<{items: ThirdEyesSignal[]; total: number}>('/signals?limit=500'); }
  acknowledge(id: string) { return this.request<ThirdEyesSignal>(`/signals/${encodeURIComponent(id)}/ack`, 'POST'); }

  /** Caller retains the last processed ID and persists it alongside its local event cache. */
  async events(after: number, receive: (event: ThirdEyesEvent) => void, abort: AbortSignal): Promise<void> {
    let cursor = after;
    while (!abort.aborted) {
      try {
        const response = await fetch(`${this.base}/third-eyes/v1/events?after=${cursor}`, {
          headers: { Authorization: `Bearer ${this.token()}` }, signal: abort,
        });
        if (!response.ok) throw new Error(`Third Eyes SSE ${response.status}`);
        if (!response.body) throw new Error('Missing SSE response body');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        try {
          for (;;) {
            const {value, done} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});
            let boundary: number;
            while ((boundary = buffer.indexOf('\n\n')) >= 0) {
              const block = buffer.slice(0, boundary);
              buffer = buffer.slice(boundary + 2);
              const lines = block.split('\n');
              const id = Number(lines.find(l => l.startsWith('id:'))?.slice(3));
              const event = lines.find(l => l.startsWith('event:'))?.slice(6).trim();
              const data = lines.filter(l => l.startsWith('data:')).map(l => l.slice(5).trim()).join('\n');
              if (id > cursor && event && data) {
                receive({id, event, data: JSON.parse(data)});
                cursor = id;
              }
            }
          }
        } finally { await reader.cancel(); }
      } catch (error) { if (abort.aborted) return; }
      if (abort.aborted) return;
      await new Promise<void>(resolve => {
        const finish = () => { clearTimeout(timer); abort.removeEventListener('abort', finish); resolve(); };
        const timer = setTimeout(finish, 1500);
        abort.addEventListener('abort', finish, {once: true});
      });
    }
  }
}
