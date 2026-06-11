/**
 * <chat-with-app> — a self-contained chat web component that drives any
 * OpenAPI-described REST backend with a Claude-powered agent loop.
 *
 * Attributes:
 *   spec-url        URL of the OpenAPI JSON spec  (default: /openapi.json)
 *   system-prompt   Override the default system prompt
 *
 * Custom events dispatched on the element:
 *   tool-executed   { detail: { name, input, result } }
 *                   Fired after every tool call so the host page can refresh
 *                   its own UI (e.g. re-render a todo list).
 *
 * Usage:
 *   <chat-with-app spec-url="/openapi.json"></chat-with-app>
 *   <script type="module" src="/chat-with-app.js"></script>
 */

const STYLES = `
  :host {
    --bg:         #0f0f11;
    --surface:    #1a1a1f;
    --border:     #2a2a32;
    --accent:     #7c6af7;
    --accent-dim: #3d3570;
    --text:       #e8e8f0;
    --muted:      #6b6b7e;
    --red:        #f76a6a;
    --green:      #6af7a8;
    --font:       'Inter', system-ui, sans-serif;
    --mono:       'JetBrains Mono', 'Fira Code', monospace;

    display: flex;
    flex-direction: column;
    width: 380px;
    height: 100%;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    overflow: hidden;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  /* Header */
  .chat-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }
  .agent-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 6px var(--green);
    flex-shrink: 0;
  }
  .chat-header-label { font-size: 13px; font-weight: 600; }
  .chat-header-sub   { font-size: 11px; color: var(--muted); margin-left: auto; }

  /* API key row */
  .api-key-row {
    display: flex;
    gap: 6px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    align-items: center;
  }
  .api-key-row label { font-size: 11px; color: var(--muted); white-space: nowrap; }
  .api-key-row input {
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-family: var(--mono);
    font-size: 11px;
    padding: 5px 8px;
    outline: none;
  }
  .api-key-row input:focus { border-color: var(--accent); }
  .api-key-row input::placeholder { color: var(--muted); }

  /* Messages */
  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .chat-msg {
    display: flex;
    flex-direction: column;
    gap: 3px;
    max-width: 92%;
  }
  .chat-msg.user      { align-self: flex-end;   align-items: flex-end; }
  .chat-msg.assistant { align-self: flex-start; align-items: flex-start; }
  .chat-msg.system    { align-self: center;     align-items: center; max-width: 100%; }

  .chat-bubble {
    font-size: 13px;
    line-height: 1.5;
    padding: 9px 12px;
    border-radius: 12px;
    word-break: break-word;
  }
  .user .chat-bubble {
    background: var(--accent);
    color: #fff;
    border-bottom-right-radius: 4px;
  }
  .assistant .chat-bubble {
    background: var(--surface);
    border: 1px solid var(--border);
    border-bottom-left-radius: 4px;
    color: var(--text);
  }
  .system .chat-bubble {
    background: transparent;
    color: var(--muted);
    font-size: 11px;
    font-style: italic;
  }

  .tool-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: var(--accent-dim);
    color: var(--accent);
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-family: var(--mono);
    margin: 3px 0;
  }

  /* Input row */
  .chat-input-row {
    display: flex;
    gap: 8px;
    padding: 12px 14px;
    border-top: 1px solid var(--border);
    flex-shrink: 0;
  }
  .chat-input-row textarea {
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-family: var(--font);
    font-size: 13px;
    padding: 8px 10px;
    outline: none;
    resize: none;
    min-height: 38px;
    max-height: 100px;
    line-height: 1.4;
    transition: border-color .15s;
  }
  .chat-input-row textarea:focus { border-color: var(--accent); }
  .chat-input-row textarea::placeholder { color: var(--muted); }

  .send-btn {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    width: 38px;
    height: 38px;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    transition: opacity .15s;
    align-self: flex-end;
  }
  .send-btn:hover    { opacity: .85; }
  .send-btn:disabled { opacity: .35; cursor: default; }

  /* Scrollbar */
  ::-webkit-scrollbar       { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

  /* Typing indicator */
  .typing { display: flex; gap: 4px; align-items: center; padding: 6px 4px; }
  .typing span {
    width: 6px; height: 6px; border-radius: 50%; background: var(--muted);
    animation: bounce 1.2s infinite;
  }
  .typing span:nth-child(2) { animation-delay: .2s; }
  .typing span:nth-child(3) { animation-delay: .4s; }
  @keyframes bounce {
    0%,60%,100% { transform: translateY(0); }
    30%          { transform: translateY(-5px); }
  }
`;

const TEMPLATE = `
  <div class="chat-header">
    <div class="agent-dot"></div>
    <span class="chat-header-label">Agent</span>
    <span class="chat-header-sub">Claude-powered</span>
  </div>

  <div class="api-key-row">
    <label>API key</label>
    <input id="apiKeyInput" type="password" placeholder="sk-ant-..." autocomplete="off" />
  </div>

  <div id="chatMessages" class="chat-messages">
    <div class="chat-msg system">
      <div class="chat-bubble">Enter your Anthropic API key above, then ask me anything.</div>
    </div>
  </div>

  <div class="chat-input-row">
    <textarea id="chatInput" placeholder="Ask the agent..." rows="1"></textarea>
    <button class="send-btn" id="sendBtn">&#x2191;</button>
  </div>
`;

// ── OpenAPI helpers (pure functions, no DOM deps) ─────────────────────────────

function resolveRef(spec, ref) {
  const parts = ref.replace(/^#\//, '').split('/');
  return parts.reduce((obj, key) => obj?.[key], spec);
}

function resolveSchema(spec, schema, depth = 0) {
  if (!schema || depth > 10) return { type: 'object', properties: {} };
  if (schema.$ref) return resolveSchema(spec, resolveRef(spec, schema.$ref), depth + 1);

  if (schema.anyOf) {
    const nonNull = schema.anyOf.filter(s => s.type !== 'null' && !s.$ref?.includes('null'));
    if (nonNull.length === 1) return resolveSchema(spec, nonNull[0], depth + 1);
    return { ...schema, anyOf: schema.anyOf.map(s => resolveSchema(spec, s, depth + 1)) };
  }

  if (schema.properties) {
    const resolved = { ...schema, properties: {} };
    for (const [k, v] of Object.entries(schema.properties))
      resolved.properties[k] = resolveSchema(spec, v, depth + 1);
    return resolved;
  }

  if (schema.type === 'array' && schema.items)
    return { ...schema, items: resolveSchema(spec, schema.items, depth + 1) };

  return schema;
}

function responseSchema(spec, operation) {
  const responses = operation.responses ?? {};
  const code = ['200', '201'].find(c => responses[c]) ?? Object.keys(responses)[0];
  const content = responses[code]?.content?.['application/json'];
  return resolveSchema(spec, content?.schema);
}

function buildFetchFn(spec, method, path, operation) {
  const pathParams = (path.match(/\{(\w+)\}/g) ?? []).map(p => p.slice(1, -1));
  const bodySchema = resolveSchema(
    spec,
    operation.requestBody?.content?.['application/json']?.schema ?? null
  );

  const inputSchema = {
    type: 'object',
    properties: {
      ...pathParams.reduce((acc, p) => {
        const paramDef = (operation.parameters ?? []).find(x => x.name === p);
        acc[p] = resolveSchema(spec, paramDef?.schema ?? { type: 'integer' });
        acc[p].description = paramDef?.description ?? p;
        return acc;
      }, {}),
      ...(bodySchema?.properties ?? {}),
    },
    required: [...pathParams, ...(bodySchema?.required ?? [])],
  };

  const outputSchema = responseSchema(spec, operation);

  const fn = async (input = {}) => {
    let url = path;
    const body = { ...input };
    for (const p of pathParams) {
      if (!(p in body)) throw new Error(`Missing path param: ${p}`);
      url = url.replace(`{${p}}`, encodeURIComponent(body[p]));
      delete body[p];
    }
    const hasBody = ['post', 'patch', 'put'].includes(method);
    const res = await fetch(url, {
      method: method.toUpperCase(),
      headers: hasBody ? { 'Content-Type': 'application/json' } : {},
      body: hasBody && Object.keys(body).length ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? `HTTP ${res.status}`);
    }
    return res.json();
  };

  fn._def = {
    description: operation.summary ?? operation.operationId,
    input: inputSchema,
    output: outputSchema,
  };
  return fn;
}

async function buildAPIFromSpec(specUrl) {
  const spec = await fetch(specUrl).then(r => r.json());
  const api = {};
  for (const [path, methods] of Object.entries(spec.paths ?? {})) {
    for (const [method, operation] of Object.entries(methods)) {
      if (!operation.operationId) continue;
      api[operation.operationId] = buildFetchFn(spec, method, path, operation);
    }
  }
  return api;
}

function deriveTools(api) {
  return Object.entries(api)
    .filter(([, fn]) => typeof fn === 'function' && fn._def)
    .map(([name, fn]) => ({
      name,
      description: fn._def.description,
      input_schema: fn._def.input,
    }));
}

function checkRequired(schema, obj) {
  return (schema?.required ?? [])
    .filter(k => obj[k] === undefined)
    .map(k => `missing required field: ${k}`);
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ── Web Component ─────────────────────────────────────────────────────────────

class ChatWithApp extends HTMLElement {
  static get observedAttributes() { return ['spec-url', 'system-prompt']; }

  constructor() {
    super();
    this._shadow      = this.attachShadow({ mode: 'open' });
    this._api         = {};
    this._tools       = [];
    this._history     = [];
    this._busy        = false;

    // Inject styles + HTML
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(STYLES);
    this._shadow.adoptedStyleSheets = [sheet];

    this._shadow.innerHTML = TEMPLATE;
  }

  connectedCallback() {
    const send    = this._shadow.getElementById('sendBtn');
    const input   = this._shadow.getElementById('chatInput');

    send.addEventListener('click', () => this._sendMessage());
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._sendMessage(); }
    });

    this._init();
  }

  // Allow host page to supply an API key programmatically
  set apiKey(value) {
    this._shadow.getElementById('apiKeyInput').value = value ?? '';
  }

  // ── Internal helpers ──────────────────────────────────────────────────────

  get _specUrl()      { return this.getAttribute('spec-url') || '/openapi.json'; }
  get _systemPrompt() {
    return this.getAttribute('system-prompt') ||
      'You are a helpful assistant with tools to manage the application data. ' +
      'Be concise and confirm what you did after using tools.';
  }

  _$(id) { return this._shadow.getElementById(id); }

  _appendMsg(role, html) {
    const box = this._$('chatMessages');
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    div.innerHTML = `<div class="chat-bubble">${html}</div>`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  _appendToolPill(name, result) {
    const box = this._$('chatMessages');
    const div = document.createElement('div');
    div.className = 'chat-msg assistant';
    div.innerHTML = `<div class="tool-pill">&#x2699; ${escHtml(name)} &rarr; ${escHtml(JSON.stringify(result).slice(0, 80))}</div>`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  _showTyping() {
    const box = this._$('chatMessages');
    const div = document.createElement('div');
    div.className = 'chat-msg assistant';
    div.id = 'typing-indicator';
    div.innerHTML = `<div class="chat-bubble"><div class="typing"><span></span><span></span><span></span></div></div>`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  _hideTyping() {
    this._shadow.getElementById('typing-indicator')?.remove();
  }

  async _callClaude(messages) {
    const apiKey = this._$('apiKeyInput').value.trim();
    if (!apiKey) throw new Error('Please enter your Anthropic API key.');

    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify({
        model:      'claude-sonnet-4-20250514',
        max_tokens: 1024,
        system:     this._systemPrompt,
        tools:      this._tools,
        messages,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.error?.message ?? `API error ${res.status}`);
    }
    return res.json();
  }

  async _executeTool(name, input) {
    const fn = this._api[name];
    if (!fn) return { error: `Unknown tool: ${name}` };

    const errors = checkRequired(fn._def.input, input);
    if (errors.length) return { error: 'Invalid input', details: errors };

    const result = await fn(input);

    // Notify the host page so it can refresh its own UI
    this.dispatchEvent(new CustomEvent('tool-executed', {
      bubbles: true,
      composed: true,
      detail: { name, input, result },
    }));

    return result;
  }

  async _sendMessage() {
    if (this._busy) return;
    const input    = this._$('chatInput');
    const sendBtn  = this._$('sendBtn');
    const userText = input.value.trim();
    if (!userText) return;

    input.value      = '';
    sendBtn.disabled = true;
    this._busy       = true;

    this._appendMsg('user', escHtml(userText));
    this._history.push({ role: 'user', content: userText });
    this._showTyping();

    try {
      while (true) {
        const data        = await this._callClaude(this._history);
        this._hideTyping();

        const toolBlocks  = data.content.filter(b => b.type === 'tool_use');
        const textBlocks  = data.content.filter(b => b.type === 'text');

        for (const b of textBlocks)
          if (b.text.trim()) this._appendMsg('assistant', escHtml(b.text));

        this._history.push({ role: 'assistant', content: data.content });

        if (toolBlocks.length > 0) {
          const toolResults = [];
          for (const tool of toolBlocks) {
            const result = await this._executeTool(tool.name, tool.input);
            this._appendToolPill(tool.name, result);
            toolResults.push({
              type: 'tool_result',
              tool_use_id: tool.id,
              content: JSON.stringify(result),
            });
          }
          this._history.push({ role: 'user', content: toolResults });
          this._showTyping();
          continue;
        }

        if (data.stop_reason === 'end_turn') break;
        console.warn('[chat-with-app] Unexpected stop_reason:', data.stop_reason);
        break;
      }
    } catch (err) {
      this._hideTyping();
      this._appendMsg('system', `&#x26A0; ${escHtml(err.message)}`);
    }

    sendBtn.disabled = false;
    this._busy       = false;
    input.focus();
  }

  async _init() {
    try {
      this._api   = await buildAPIFromSpec(this._specUrl);
      this._tools = deriveTools(this._api);
      this._appendMsg('system', `API ready &mdash; ${this._tools.length} tools loaded.`);
    } catch (e) {
      this._appendMsg('system', `&#x26A0; Could not reach backend: ${escHtml(e.message)}`);
    }
  }
}

customElements.define('chat-with-app', ChatWithApp);
