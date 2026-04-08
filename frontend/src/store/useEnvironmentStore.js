/**
 * Zustand store for environment state.
 * Manages all UI state: current task, observation, history, loading states.
 */

import { create } from 'zustand';
import api from '../services/api';

const useEnvironmentStore = create((set, get) => ({
  // --- State ---
  tasks: [],
  selectedTask: 'fizzbuzz_fix',
  sessionId: null,
  observation: null,
  envState: null,
  history: [],
  rewards: [],
  isLoading: false,
  isResetting: false,
  isStepping: false,
  isAutoRunning: false,
  error: null,
  isInitialized: false,
  customBuggyCode: '',
  customTestCode: '',

  // --- Experiment State ---
  experimentData: null,
  isExperimentRunning: false,
  experimentError: null,
  experimentPhase: 0, // 0=idle, 1=running, 2=done(show blind), 3=toggle, 4=show reflection, 5=results
  activeView: 'agent', // 'agent' or 'experiment'

  // Live streaming state (for agent thinking visualization)
  experimentLiveMode: null,       // 'blind' | 'reflection' | null
  experimentLiveStep: null,       // current step number being processed
  experimentLiveMaxSteps: 8,      // max steps per episode
  experimentLiveSteps: [],        // steps for the currently-running agent
  experimentBlindSteps: [],       // accumulated blind episode steps
  experimentReflectionSteps: [],  // accumulated reflection episode steps
  experimentIsThinking: false,    // true while waiting for LLM response
  experimentBlindResult: null,    // blind episode summary (set on phase_end)
  experimentReflectionResult: null, // reflection episode summary
  _experimentEventSource: null,   // internal: EventSource reference for cleanup

  // --- Actions ---

  /** Switch between agent and experiment views */
  setActiveView: (view) => set({ activeView: view }),

  /** Set experiment phase for story animation */
  setExperimentPhase: (phase) => set({ experimentPhase: phase }),

  /** Fetch available tasks from backend */
  fetchTasks: async () => {
    try {
      const data = await api.getTasks();
      set({ tasks: data.tasks || [] });
    } catch (err) {
      set({ error: err.message });
    }
  },

  /** Select a task */
  selectTask: (taskName) => {
    set({ selectedTask: taskName });
  },

  /** Update custom codes */
  setCustomCode: (buggy, tests) => {
    set({ customBuggyCode: buggy, customTestCode: tests });
  },

  /** Stop auto running */
  stopAutoRun: () => set({ isAutoRunning: false }),

  /** Reset environment with selected task */
  resetEnvironment: async (taskName, customBuggyCode = null, customTestCode = null) => {
    const task = taskName || get().selectedTask;
    set({ isResetting: true, error: null, history: [], rewards: [] });
    try {
      const data = await api.reset(task, null, customBuggyCode, customTestCode);
      set({
        sessionId: data.session_id,
        observation: data.observation,
        isResetting: false,
        isInitialized: true,
        history: [],
        rewards: [],
      });
    } catch (err) {
      set({ isResetting: false, error: err.message });
    }
  },

  /** Automatically run a step through the agent */
  autoStep: async () => {
    const { sessionId } = get();
    if (!sessionId) {
      set({ error: 'No active session. Reset first.' });
      return;
    }
    set({ isStepping: true, error: null });
    try {
      const data = await api.autoStep(sessionId);
      const obs = data.observation;
      const reward = data.reward || 0;
      const action = data.action;

      const prevHistory = get().history;
      const stepEntry = {
        step: obs.step_number,
        tests_passed: obs.tests_passed,
        tests_total: obs.tests_total,
        reward: reward,
        reward_breakdown: obs.reward_breakdown,
        hypothesis: action?.hypothesis || 'No hypothesis',
        action_description: action?.action_description || 'No action',
        expected_result: action?.expected_result || 'No expected result',
        done: data.done,
      };

      set({
        observation: obs,
        isStepping: false,
        history: [...prevHistory, stepEntry],
        rewards: [...get().rewards, reward],
      });
    } catch (err) {
      set({ isStepping: false, error: err.message, isAutoRunning: false });
    }
  },

  /** Continuously run steps until done or error */
  autoRun: async () => {
    set({ isAutoRunning: true, error: null });
    while (get().isAutoRunning && !get().observation?.done && !get().error) {
       await get().autoStep();
    }
    set({ isAutoRunning: false });
  },

  /** Run A/B experiment with live SSE streaming */
  runExperiment: (taskName) => {
    const task = taskName || get().selectedTask;

    // Clean up any previous stream
    const prev = get()._experimentEventSource;
    if (prev) prev.close();

    set({
      isExperimentRunning: true,
      experimentError: null,
      experimentData: null,
      experimentPhase: 1,
      experimentLiveMode: null,
      experimentLiveStep: null,
      experimentLiveSteps: [],
      experimentBlindSteps: [],
      experimentReflectionSteps: [],
      experimentIsThinking: false,
      experimentBlindResult: null,
      experimentReflectionResult: null,
    });

    const source = api.streamExperiment(
      task,
      // onEvent callback — handle each SSE event
      (event) => {
        switch (event.type) {
          case 'phase_start':
            set({
              experimentLiveMode: event.mode,
              experimentLiveSteps: [],
              experimentIsThinking: false,
              experimentLiveStep: null,
            });
            break;

          case 'thinking':
            set({
              experimentIsThinking: true,
              experimentLiveStep: event.step,
              experimentLiveMaxSteps: event.max_steps || 8,
            });
            break;

          case 'step': {
            const mode = event.mode;
            const stepData = event.data;
            const liveSteps = [...get().experimentLiveSteps, stepData];
            const updates = {
              experimentIsThinking: false,
              experimentLiveSteps: liveSteps,
            };
            if (mode === 'blind') {
              updates.experimentBlindSteps = [...get().experimentBlindSteps, stepData];
            } else {
              updates.experimentReflectionSteps = [...get().experimentReflectionSteps, stepData];
            }
            set(updates);
            break;
          }

          case 'phase_end':
            if (event.mode === 'blind') {
              set({ experimentBlindResult: event.result });
            } else {
              set({ experimentReflectionResult: event.result });
            }
            break;

          case 'complete':
            set({
              experimentData: event,
              isExperimentRunning: false,
              experimentPhase: 2,
              experimentLiveMode: null,
              experimentIsThinking: false,
              _experimentEventSource: null,
            });
            break;

          case 'error':
            set({
              isExperimentRunning: false,
              experimentError: event.message || 'Experiment stream failed',
              experimentPhase: 0,
              _experimentEventSource: null,
            });
            break;

          default:
            break;
        }
      },
      // onError callback
      (err) => {
        set({
          isExperimentRunning: false,
          experimentError: 'Connection to experiment stream lost',
          experimentPhase: 0,
          _experimentEventSource: null,
        });
      }
    );

    set({ _experimentEventSource: source });
  },

  /** Clear experiment data */
  clearExperiment: () => {
    const prev = get()._experimentEventSource;
    if (prev) prev.close();
    set({
      experimentData: null,
      experimentError: null,
      experimentPhase: 0,
      experimentLiveMode: null,
      experimentLiveStep: null,
      experimentLiveSteps: [],
      experimentBlindSteps: [],
      experimentReflectionSteps: [],
      experimentIsThinking: false,
      experimentBlindResult: null,
      experimentReflectionResult: null,
      _experimentEventSource: null,
    });
  },

  /** Fetch current state */
  fetchState: async () => {
    const { sessionId } = get();
    try {
      const data = await api.getState(sessionId);
      set({ envState: data.state });
    } catch (err) {
      set({ error: err.message });
    }
  },

  /** Clear error */
  clearError: () => set({ error: null }),
}));

export default useEnvironmentStore;
