const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  getGarden: () => request('/garden'),
  getEcosystem: () => request('/ecosystem'),
  getPulse: () => request('/pulse'),
  getPulseHistory: (n = 5) => request(`/pulse/history?limit=${n}`),
  getSeasons: () => request('/seasons'),
  getDreams: () => request('/dreams'),
  getWounds: (n = 10) => request(`/wounds?limit=${n}`),
  getMycelium: () => request('/mycelium'),
  getSoilRichness: () => request('/soil/richness'),
  getHormones: (n = 20) => request(`/hormones/recent?n=${n}`),
  getSeed: (id) => request(`/seed/${id}`),

  plant: (wish, gardenerId = null) =>
    request('/plant', {
      method: 'POST',
      body: JSON.stringify({ wish, gardener_id: gardenerId }),
    }),

  plantMany: (wishes) =>
    request('/plant/many', {
      method: 'POST',
      body: JSON.stringify({ wishes }),
    }),

  water: (seedId, seconds = 5) =>
    request(`/seed/${seedId}/water`, {
      method: 'POST',
      body: JSON.stringify({ attention_seconds: seconds, energy_boost: 5 }),
    }),

  harvest: (seedId) => request(`/seed/${seedId}/harvest`, { method: 'POST' }),
  compost: (seedId) => request(`/seed/${seedId}/compost`, { method: 'POST' }),
  resurrect: (seedId) => request(`/seed/${seedId}/resurrect`, { method: 'POST' }),
  plantDream: (dreamId) => request(`/dreams/${dreamId}/plant`, { method: 'POST' }),
  turnSeason: (force = null) =>
    request(`/seasons/turn${force ? `?force=${force}` : ''}`, { method: 'POST' }),

  getOllamaStatus: () => request('/ollama/status'),
  getLifecycleStatus: () => request('/lifecycle/status'),

  // Agents
  getAgents: (includeRetired = false) => request(`/agents?include_retired=${includeRetired}`),
  getAgent: (id) => request(`/agents/${id}`),
  approveAgent: (id, approved) =>
    request(`/agents/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved }),
    }),
  retireAgent: (id) => request(`/agents/${id}/retire`, { method: 'POST' }),

  // Consciousness
  getConsciousness: () => request('/consciousness'),
  getEmotions: () => request('/consciousness/emotions'),
  getThoughts: (limit = 20) => request(`/consciousness/thoughts?limit=${limit}`),
  getMemories: (limit = 20) => request(`/consciousness/memories?limit=${limit}`),
  getPredictions: () => request('/consciousness/predictions'),
  getSelfModel: () => request('/consciousness/self'),
};
