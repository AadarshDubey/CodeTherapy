import React from 'react';
import useEnvironmentStore from '../store/useEnvironmentStore';
import './Header.css';

export default function Header() {
  const observation = useEnvironmentStore((s) => s.observation);
  const isInitialized = useEnvironmentStore((s) => s.isInitialized);
  const selectedTask = useEnvironmentStore((s) => s.selectedTask);

  const stepNum = observation?.step_number || 0;
  const maxSteps = observation?.max_steps || 8;

  return (
    <header className="header" id="header">
      <div className="header-left">
        <div className="header-icon">🔬</div>
        <div>
          <h1 className="header-title">Reflection Debug Agent</h1>
          <p className="header-subtitle">OpenEnv • Reflection-Guided Debugging</p>
        </div>
      </div>
      <div className="header-right">
        <div className="header-status">
          <span className={`header-status-dot ${isInitialized ? '' : 'inactive'}`}></span>
          {isInitialized ? 'Environment Active' : 'Not Started'}
        </div>
        {isInitialized && (
          <span className="header-step-badge">
            Step {stepNum} / {maxSteps}
          </span>
        )}
      </div>
    </header>
  );
}
