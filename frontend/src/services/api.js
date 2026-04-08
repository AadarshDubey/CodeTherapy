/**
 * API service — wraps all backend HTTP calls.
 */

const BASE_URL = '';

async function fetchJSON(url, options = {}) {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  /** List available tasks */
  getTasks: () => fetchJSON('/api/tasks'),

  /** Get details of a specific task */
  getTask: (taskName) => fetchJSON(`/api/task/${taskName}`),

  /** Reset environment with a task */
  reset: (taskName, sessionId = null, customBuggyCode = null, customTestCode = null) =>
    fetchJSON('/api/reset', {
      method: 'POST',
      body: JSON.stringify({
        task_name: taskName,
        session_id: sessionId,
        custom_buggy_code: customBuggyCode,
        custom_test_code: customTestCode,
      }),
    }),

  /** Take a step in the environment */
  step: (sessionId, action) =>
    fetchJSON('/api/step', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        edits: action.edits,
        hypothesis: action.hypothesis,
        action_description: action.action_description,
        expected_result: action.expected_result,
      }),
    }),

  /** Automatically run agent step */
  autoStep: (sessionId) =>
    fetchJSON('/api/auto_step', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
      }),
    }),

  /** Get current state */
  getState: (sessionId) =>
    fetchJSON(`/api/state?session_id=${sessionId || ''}`),

  /** Get step history */
  getHistory: (sessionId) =>
    fetchJSON(`/api/history?session_id=${sessionId || ''}`),

  /** Run A/B experiment (blind vs reflection) */
  runExperiment: (taskName) =>
    fetchJSON('/api/experiment/run', {
      method: 'POST',
      body: JSON.stringify({ task_name: taskName }),
    }),

  /** Stream A/B experiment via SSE (real-time agent thinking) */
  streamExperiment: (taskName, onEvent, onError) => {
    const url = `/api/experiment/stream?task_name=${encodeURIComponent(taskName)}`;
    const source = new EventSource(url);

    const eventTypes = ['phase_start', 'thinking', 'step', 'phase_end', 'complete', 'error'];

    const handler = (e) => {
      try {
        const data = JSON.parse(e.data);
        onEvent(data);
        if (data.type === 'complete' || data.type === 'error') {
          source.close();
        }
      } catch (err) {
        console.error('[SSE] Parse error:', err);
      }
    };

    // Listen for each named event type from the backend
    eventTypes.forEach((type) => source.addEventListener(type, handler));

    // Also listen for generic 'message' events (fallback)
    source.onmessage = handler;

    source.onerror = (err) => {
      console.error('[SSE] Connection error:', err);
      source.close();
      if (onError) onError(err);
    };
    return source;
  },

  /** Health check */
  health: () => fetchJSON('/health'),
};

export default api;
