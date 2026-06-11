# Chrome Extension: chat-with-app companion

## Motivation

The `<chat-with-app>` web component requires the developer to embed it in the page.
A companion Chrome extension makes the chat available on **any** OpenAPI-backed app
without any developer action — including apps you don't control.

---

## Core idea

1. User installs the extension and enters their Anthropic API key once.
2. On every page visit, the extension tries `GET <origin>/openapi.json`.
3. If it resolves, the extension injects `<chat-with-app>` into the page automatically.
4. The chat panel appears with all tools derived from the spec — no developer action needed.

This turns the web component into a **universal AI chat overlay** for any OpenAPI app:
FastAPI, Django REST Framework, Rails, internal tools, local dev servers, etc.

---

## API key storage

The user enters their Anthropic API key once in the extension popup.
It is stored in `chrome.storage.sync` (synced across the user's devices).

```
Extension popup → chrome.storage.sync
                         ↓
        Content script reads key on each page
                         ↓
        Injected <chat-with-app> receives key programmatically
        (via the element's apiKey setter — never via a visible input)
```

The key input in the web component is hidden when the key is supplied by the extension.

### Per-origin permission grants

When the extension detects an OpenAPI spec on a new origin, it prompts the user:

> "chat-with-app: Allow this site to use your Anthropic API key?"
> [ Allow ] [ Deny ] [ Always allow this domain ]

Granted origins are stored in `chrome.storage.local`. On subsequent visits the check
is silent.

### localStorage note

`localStorage` is origin-scoped by the browser, so a key stored on `app1.acme.com`
is not accessible on `app2.acme.com`. The extension solves this — the key is stored
once in `chrome.storage.sync` and shared across all granted origins.

---

## Swagger page support

Swagger UI pages (`/docs` on FastAPI, `/swagger` on others) are a first-class target.
On these pages the user is typically a developer exploring or testing an API.

### Detecting a Swagger page

```js
const isSwagger = !!window.ui?.authSelectors;  // Swagger UI instance present
```

Alternatively detect via the page title or the presence of `.swagger-ui` in the DOM.

### Extracting the spec URL

Swagger UI advertises the spec URL it loaded — use it instead of guessing:

```js
const specUrl = window.ui?.getConfigs?.()?.url    // Swagger UI internal config
             ?? document.querySelector('[data-spec-url]')?.dataset.specUrl
             ?? location.origin + '/openapi.json'; // fallback
```

### Chat use cases on Swagger pages

On a Swagger page the agent acts as a documentation assistant + live API client:

- "What endpoints are available?"
- "What fields are required for POST /orders?"
- "Call GET /todos and show me the results."
- "Show me a curl example for creating a user."
- "What does a 422 response mean for this endpoint?"

---

## Bearer token capture (Swagger pages)

The user authenticates manually via Swagger UI's "Authorize" dialog.
Credentials are **never shared with the agent** — only the resulting Bearer token
is captured, purely at the infrastructure level.

### Why not let the agent handle auth?

Entering credentials into the chat would mean the LLM sees them. The agent
should only call data tools (list, create, update, delete). Auth is plumbing.

### Capture strategies (in priority order)

#### 1. Subscribe to Swagger's Redux store (cleanest)

Fires exactly when auth state changes, no polling, no DOM coupling:

```js
window.ui?.getStore?.()?.subscribe(() => {
  const token = getSwaggerToken();
  if (token && token !== current) {
    current = token;
    injectToken(token);
  }
});

function getSwaggerToken() {
  const auth = window.ui?.authSelectors?.authorized()?.toJS?.() ?? {};
  const scheme = Object.values(auth)[0];
  return scheme?.value ?? null;
}
```

#### 2. MutationObserver on lock icons (reliable fallback)

Swagger renders padlock icons that switch from open to closed after auth:

```js
const observer = new MutationObserver(() => {
  const isLocked = document.querySelector('.authorization__btn.locked');
  if (isLocked) {
    const token = getSwaggerToken();
    if (token) { injectToken(token); observer.disconnect(); }
  }
});
observer.observe(document.body, { subtree: true, childList: true, attributes: true });
```

#### 3. Fetch sniffing (works on any app, not just Swagger)

Wrap `window.fetch` early. Token is captured when the user clicks "Execute"
on any authenticated endpoint:

```js
const origFetch = window.fetch;
window.fetch = async (url, opts = {}) => {
  const auth = opts.headers?.['Authorization'] ?? opts.headers?.['authorization'];
  if (auth?.startsWith('Bearer ') && new URL(url).origin === location.origin) {
    injectToken(auth.slice(7));
  }
  return origFetch(url, opts);
};
```

#### 4. Polling (last resort)

```js
const poll = setInterval(() => {
  const token = getSwaggerToken();
  if (token && token !== current) { injectToken(token); clearInterval(poll); }
}, 1000);
```

### Decision tree

```
Is window.ui?.getStore available?  → subscribe (option 1)
        ↓ no
Is this a Swagger page?            → MutationObserver on lock icons (option 2)
        ↓ no
Any app                            → fetch sniffing (option 3)
```

### Token injection into the fetch layer

Once captured, the token is wired into every API call made by the agent.
The agent itself never sees or handles the token:

```js
function injectToken(token) {
  // Patch the fetch functions already built by buildAPIFromSpec
  // so they include the Authorization header going forward.
  chatComponent.setBearerToken(token);
}
```

In `chat-with-app.js`, `setBearerToken` stores the value and `buildFetchFn`
reads it at call time:

```js
headers: {
  ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
  ...(this._bearerToken ? { 'Authorization': `Bearer ${this._bearerToken}` } : {}),
}
```

The agent calls `list_orders()` and gets data — it has no knowledge of the token.

---

## APIs that issue tokens via a login endpoint

Some APIs expose a `POST /auth/token` (or similar) endpoint in their OpenAPI spec
that accepts `username` + `password` and returns a Bearer token.

**The user should authenticate manually** via Swagger's Authorize dialog rather than
through the chat, so credentials never reach the LLM.

If the user does type credentials into chat, the token returned by the login tool
call can be auto-captured:

```js
// In _executeTool, after the call returns:
const token = result.access_token ?? result.token ?? result.id_token;
if (token) this._bearerToken = token;
```

The spec's `securitySchemes` section advertises the token URL:

```json
"securitySchemes": {
  "OAuth2PasswordBearer": {
    "type": "oauth2",
    "flows": { "password": { "tokenUrl": "token" } }
  }
}
```

This can be read at init time to inform the system prompt:

```js
const tokenUrl = Object.values(spec.components?.securitySchemes ?? {})
  .find(s => s.flows?.password?.tokenUrl)
  ?.flows.password.tokenUrl;

if (tokenUrl) systemPrompt += `\nAuthentication endpoint: ${tokenUrl}`;
```

---

## Two distribution channels

| | Web component | Chrome extension |
|---|---|---|
| Target audience | Developers embedding chat in their own app | End users wanting chat on any app they visit |
| API key entry | Once per origin (or hidden if extension present) | Once ever, synced across devices |
| Works without the other | Yes | Yes |
| Bearer token capture | Via fetch sniffing on the same page | Via content script on any page |
| Swagger support | Yes (when embedded on the Swagger page) | Yes (auto-injected on any Swagger page) |

The two are complementary. A developer can embed `<chat-with-app>` for their users,
while power users can install the extension to get chat on every OpenAPI app they visit.
