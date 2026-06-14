import axios from 'axios';

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function sendMessage(question, sessionId = null) {
  const { data } = await axios.post(`${BASE}/chat`, { question, session_id: sessionId });
  return data;
}
