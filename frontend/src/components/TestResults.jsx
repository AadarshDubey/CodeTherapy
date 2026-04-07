import React from 'react';
import useEnvironmentStore from '../store/useEnvironmentStore';
import './TestResults.css';

export default function TestResults() {
  const observation = useEnvironmentStore((s) => s.observation);

  const passed = observation?.tests_passed || 0;
  const total = observation?.tests_total || 0;
  const output = observation?.test_output || '';
  const allPass = passed === total && total > 0;
  const pct = total > 0 ? (passed / total) * 100 : 0;

  const progressClass = allPass ? 'full' : passed > 0 ? 'partial' : 'none';

  // Colorize output lines
  const renderOutput = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
      let cls = 'test-line-info';
      if (line.includes('PASS')) cls = 'test-line-pass';
      else if (line.includes('FAIL')) cls = 'test-line-fail';
      else if (line.includes('ERROR')) cls = 'test-line-error';
      return (
        <span key={i} className={cls}>
          {line}
          {'\n'}
        </span>
      );
    });
  };

  return (
    <div className="glass-panel test-results" id="test-results">
      <div className="test-results-header">
        <span className="test-results-title">
          <span>🧪</span> Test Results
        </span>
        {total > 0 && (
          <span className={`test-results-count ${allPass ? 'all-pass' : 'some-fail'}`}>
            {passed}/{total} passed
          </span>
        )}
      </div>

      {total > 0 && (
        <div className="test-results-progress">
          <div
            className={`test-results-progress-bar ${progressClass}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      {output ? (
        <div className="test-results-output">
          {renderOutput(output)}
        </div>
      ) : (
        <div className="test-results-empty">
          No test results yet. Reset the environment to start.
        </div>
      )}
    </div>
  );
}
