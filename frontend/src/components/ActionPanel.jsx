import React, { useState } from 'react';
import useEnvironmentStore from '../store/useEnvironmentStore';
import './ActionPanel.css';

export default function ActionPanel() {
  const observation = useEnvironmentStore((s) => s.observation);
  const isInitialized = useEnvironmentStore((s) => s.isInitialized);
  const isResetting = useEnvironmentStore((s) => s.isResetting);
  const isStepping = useEnvironmentStore((s) => s.isStepping);
  const isAutoRunning = useEnvironmentStore((s) => s.isAutoRunning);
  const error = useEnvironmentStore((s) => s.error);
  const selectedTask = useEnvironmentStore((s) => s.selectedTask);
  const resetEnvironment = useEnvironmentStore((s) => s.resetEnvironment);
  const customBuggyCode = useEnvironmentStore((s) => s.customBuggyCode);
  const customTestCode = useEnvironmentStore((s) => s.customTestCode);
  const autoRun = useEnvironmentStore((s) => s.autoRun);
  const stopAutoRun = useEnvironmentStore((s) => s.stopAutoRun);
  const clearError = useEnvironmentStore((s) => s.clearError);

  const [autoRunning, setAutoRunning] = useState(false);

  const isDone = observation?.done || false;
  const isSuccess = isDone && observation?.tests_total > 0 && observation?.tests_passed === observation?.tests_total;

  const handleReset = async () => {
    clearError();
    stopAutoRun();
    await resetEnvironment(selectedTask, customBuggyCode, customTestCode);
  };

  const handleAutoRun = async () => {
    clearError();
    await autoRun();
  };

  return (
    <div className="glass-panel action-panel" id="action-panel">
      <div className="action-panel-title">
        <span>🎮</span> Actions
      </div>

      <div className="action-panel-buttons">
        <button
          className="btn-primary"
          onClick={handleReset}
          disabled={isResetting}
          id="btn-reset"
        >
          {isResetting ? '⟳ Resetting...' : '🔄 Reset Environment'}
        </button>
      </div>

      {error && (
        <div className="action-panel-error">
          ⚠️ {error}
        </div>
      )}

      {isDone && isSuccess && (
        <div className="action-panel-done">
          <span>🏆</span>
          Success! All tests passed. Episode complete.
        </div>
      )}
      {isDone && !isSuccess && (
        <div className="action-panel-failed">
          <span>📉</span>
          Episode Failed: Max steps reached. Reset to try again.
        </div>
      )}

      {isInitialized && !isDone && (
        <div className="action-panel-form">
          <div className="action-panel-submit" style={{ display: 'flex', justifyContent: 'center', margin: '2rem 0', gap: '1rem' }}>
            <button
              className="btn-primary"
              onClick={handleAutoRun}
              disabled={isAutoRunning || isStepping}
              id="btn-run-loop"
              style={{ padding: '1rem 2rem', fontSize: '1.2rem', borderRadius: '8px' }}
            >
              {isAutoRunning || isStepping ? '⟳ Agent is Looping...' : '▶️ Run Full Agent Loop'}
            </button>
            {isAutoRunning && (
              <button
                className="btn-secondary"
                onClick={() => stopAutoRun()}
                style={{ padding: '1rem 2rem', fontSize: '1.2rem', borderRadius: '8px', backgroundColor: '#e74c3c', color: 'white' }}
              >
                ⏹ Stop Agent
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
