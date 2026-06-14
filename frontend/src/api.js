import axios from 'axios';

const FUNCTION_URL = 'https://project-rainfall-60074201340.development.catalystserverless.in/server/sahayak_api/execute';
const LOCAL_URL    = 'http://localhost:8000';

// In production (Slate), call the Catalyst Function directly.
// In dev (localhost), call the FastAPI backend for speed.
const isProd = import.meta.env.PROD;
const VITE_API = import.meta.env.VITE_API_URL;

function callFunction(payload) {
  // Catalyst Basic IO reads via ?input=<json>
  const params = new URLSearchParams({ input: JSON.stringify(payload) });
  return axios.get(`${FUNCTION_URL}?${params}`)
    .then(res => {
      // Function wraps response in {"output": "<json_string>"}
      const raw = res.data?.output ?? res.data;
      return typeof raw === 'string' ? JSON.parse(raw) : raw;
    });
}

function callLocal(question, sessionId) {
  return axios.post(`${LOCAL_URL}/chat`, { question, session_id: sessionId })
    .then(res => res.data);
}

export async function sendMessage(question, sessionId = null) {
  if (!isProd && !VITE_API) {
    // Dev: use local FastAPI
    return callLocal(question, sessionId);
  }
  // Production: use Catalyst Function
  const data = await callFunction({ action: 'chat', question, session_id: sessionId });
  // Normalise to the same shape FastAPI returns
  return {
    session_id: sessionId || 'catalyst',
    question,
    answer:    data.answer   ?? data.error ?? 'No response',
    sql:       data.sql      ?? null,
    columns:   data.columns  ?? [],
    rows:      data.rows     ?? [],
    row_count: data.row_count ?? 0,
    error:     data.error    ?? null,
  };
}
