import axios from 'axios';

const APPSAIL_URL = 'https://sahayak-backend-50043102650.development.catalystappsail.in';
const LOCAL_URL   = 'http://localhost:8000';

const BASE = import.meta.env.PROD ? APPSAIL_URL : LOCAL_URL;

export async function sendMessage(question, sessionId = null) {
  const { data } = await axios.post(`${BASE}/chat`, {
    question,
    session_id: sessionId,
  });
  return data;
}
