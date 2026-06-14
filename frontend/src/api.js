import axios from 'axios';

const APPSAIL_URL = 'https://sahayak-backend-50043102650.development.catalystappsail.in';
const LOCAL_URL   = 'http://localhost:8000';

const BASE = import.meta.env.PROD ? APPSAIL_URL : LOCAL_URL;

export async function sendMessage(question, sessionId = null) {
  // Use GET to avoid CORS preflight (Catalyst proxy strips OPTIONS responses).
  // The GET /chat endpoint accepts question + session_id as query params.
  const params = new URLSearchParams({ question });
  if (sessionId) params.set('session_id', sessionId);

  const { data } = await axios.get(`${BASE}/chat?${params}`);
  return data;
}
