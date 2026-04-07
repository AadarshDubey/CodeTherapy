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

  /** Run A/B experiment */
  runExperiment: async (taskName) => {
    const task = taskName || get().selectedTask;
    set({
      isExperimentRunning: true,
      experimentError: null,
      experimentData: null,
      experimentPhase: 1,
    });
    try {
      const data = await api.runExperiment(task);
      set({
        experimentData: data,
        isExperimentRunning: false,
        experimentPhase: 2,
      });
    } catch (err) {
      set({
        isExperimentRunning: false,
        experimentError: err.message,
        experimentPhase: 0,
      });
    }
  },

  /** Clear experiment data */
  clearExperiment: () => set({
    experimentData: null,
    experimentError: null,
    experimentPhase: 0,
  }),

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
