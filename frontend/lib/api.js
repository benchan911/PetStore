const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';

function getToken() {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('carepets_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const isFormData = options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('carepets_token');
    localStorage.removeItem('carepets_user');
    if (typeof window !== 'undefined') window.location.href = '/login';
    return;
  }

  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

export const api = {
  auth: {
    signup: (body) => request('/auth/signup', { method: 'POST', body: JSON.stringify(body) }),
    login: (body) => request('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
    logout: () => request('/auth/logout', { method: 'POST' }),
    me: () => request('/auth/me'),
  },
  users: {
    get: (id) => request(`/users/${id}`),
    update: (id, body) => request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
    caretakers: (params) =>
      request(`/users/caretakers${params ? '?' + new URLSearchParams(params) : ''}`),
  },
  pets: {
    list: () => request('/pets'),
    create: (body) => request('/pets', { method: 'POST', body: JSON.stringify(body) }),
    get: (id) => request(`/pets/${id}`),
    update: (id, body) => request(`/pets/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
    delete: (id) => request(`/pets/${id}`, { method: 'DELETE' }),
  },
  bookings: {
    list: (params) =>
      request(`/bookings${params ? '?' + new URLSearchParams(params) : ''}`),
    create: (body) => request('/bookings', { method: 'POST', body: JSON.stringify(body) }),
    get: (id) => request(`/bookings/${id}`),
    delete: (id) => request(`/bookings/${id}`, { method: 'DELETE' }),
    apply: (id, body) =>
      request(`/bookings/${id}/apply`, { method: 'POST', body: JSON.stringify(body) }),
    confirm: (id, body) =>
      request(`/bookings/${id}/confirm`, { method: 'POST', body: JSON.stringify(body) }),
    withdraw: (bookingId, applicationId) =>
      request(`/bookings/${bookingId}/applications/${applicationId}`, { method: 'DELETE' }),
    reject: (bookingId, applicationId) =>
      request(`/bookings/${bookingId}/applications/${applicationId}/reject`, { method: 'POST' }),
  },
};
