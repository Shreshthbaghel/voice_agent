import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({ baseURL: BASE_URL, timeout: 120_000 });

// ─── Auth interceptor ───────────────────────────────────────────────────────
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// ─── Auth ───────────────────────────────────────────────────────────────────
export async function loginUser(email, password) {
  const { data } = await client.post('/auth/login', { email, password });
  return data;
}

export async function registerUser(name, email, password) {
  const { data } = await client.post('/auth/register', { name, email, password });
  return data;
}

export async function getMe() {
  const { data } = await client.get('/auth/me');
  return data;
}

// ─── Voice ──────────────────────────────────────────────────────────────────
export async function getToken(voiceProvider, conversationId) {
  const payload = { participant_name: 'user', voice_provider: voiceProvider };
  if (conversationId) payload.conversation_id = conversationId;
  const { data } = await client.post('/voice/token', payload);
  return data;
}

// ─── Query ──────────────────────────────────────────────────────────────────
export async function queryMedicine(query, conversationId) {
  const body = { query };
  if (conversationId) body.conversation_id = conversationId;
  const { data } = await client.post('/query', body);
  return data;
}

// ─── History ────────────────────────────────────────────────────────────────
export async function getHistory() {
  const { data } = await client.get('/history');
  return data;
}

export async function getHistoryDetail(sessionId) {
  const { data } = await client.get(`/history/${sessionId}`);
  return data;
}

export async function endSession(sessionId, medicineName) {
  const { data } = await client.post(`/history/sessions/${sessionId}/end`, {
    medicine_name: medicineName,
  });
  return data;
}

export function getApiBaseUrl() {
  return BASE_URL;
}

export default client;
