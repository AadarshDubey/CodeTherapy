import React from 'react';
import useEnvironmentStore from '../store/useEnvironmentStore';
import './ReflectionPanel.css';

export default function ReflectionPanel() {
  const history = useEnvironmentStore((s) => s.history);
  const observation = useEnvironmentStore((s) => s.observation);

  const lastStep = history.length > 0 ? history[history.length - 1] : null;

  return (
    <div className="glass-panel reflection-panel" id="reflection-panel">
      <div className="reflection-panel-title">
        <span>🧠</span> Agent Reflection
      </div>

      {lastStep ? (
        <>
          <div className="reflection-section">
            <div className="reflection-section-label reflection-label-hypothesis">
              💡 Hypothesis
            </div>
            <p>{lastStep.hypothesis || '—'}</p>
          </div>
          <div className="reflection-section">
            <div className="reflection-section-label reflection-label-action">
              ⚡ Action Taken
            </div>
            <p>{lastStep.action_description || '—'}</p>
          </div>
          <div className="reflection-section">
            <div className="reflection-section-label reflection-label-result">
              🎯 Expected Result
            </div>
            <p>{lastStep.expected_result || '—'}</p>
          </div>
        </>
      ) : (
        <div className="reflection-empty">
          No reflections yet. Take a debugging step to see the agent's reasoning.
        </div>
      )}

      {observation?.reflection_prompt && !observation?.done && (
        <div className="reflection-prompt-box">
          <div className="reflection-prompt-label">Next Reflection Prompt</div>
          <p>{observation.reflection_prompt.slice(0, 200)}...</p>
        </div>
      )}
    </div>
  );
}
