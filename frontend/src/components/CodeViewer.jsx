import React from 'react';
import useEnvironmentStore from '../store/useEnvironmentStore';
import './CodeViewer.css';

export default function CodeViewer() {
  const observation = useEnvironmentStore((s) => s.observation);
  const code = observation?.buggy_code || '';

  if (!code) {
    return (
      <div className="glass-panel code-viewer" id="code-viewer">
        <div className="code-viewer-header">
          <span className="code-viewer-title">
            <span className="code-viewer-title-icon">📝</span>
            Code
          </span>
        </div>
        <div className="code-viewer-empty">
          <div className="code-viewer-empty-icon">💻</div>
          <p>Reset the environment to load buggy code.</p>
        </div>
      </div>
    );
  }

  const lines = code.split('\n');

  return (
    <div className="glass-panel code-viewer" id="code-viewer">
      <div className="code-viewer-header">
        <span className="code-viewer-title">
          <span className="code-viewer-title-icon">📝</span>
          Code Under Test
        </span>
        <span className="code-viewer-language">Python</span>
      </div>
      <div className="code-viewer-content">
        <pre className="code-viewer-pre">
          <code>
            {lines.map((line, i) => (
              <span key={i} className="code-viewer-line">
                {line || ' '}
                {'\n'}
              </span>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
}
