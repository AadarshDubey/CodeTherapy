import React from 'react';
import useEnvironmentStore from '../store/useEnvironmentStore';
import './StepHistory.css';

export default function StepHistory() {
  const history = useEnvironmentStore((s) => s.history);

  const getStepClass = (step, index) => {
    if (index === 0) return 'same';
    const prev = history[index - 1];
    if (step.tests_passed > prev.tests_passed) return 'improved';
    if (step.tests_passed < prev.tests_passed) return 'regressed';
    return 'same';
  };

  const renderInterpretabilityBadge = (step) => {
    const sub = step.reward_breakdown?.reflection_sub_scores || step.reflection_sub_scores;
    if (!sub) return null;

    if (sub.s_bug < 0.4) {
      return <span className="badge badge-failure" title="Low bug identification score">🔴 Poor Hypothesis</span>;
    }
    if (sub.s_improve >= 0.4 && sub.s_bug >= 0.7) {
      return <span className="badge badge-recovery" title="High reasoning & successful fix">🟢 Good Reasoning - Recovery</span>;
    }
    return null;
  };

  return (
    <div className="glass-panel step-history" id="step-history">
      <div className="step-history-title">
        <span>📜</span> Step History & Interpretability
      </div>

      {history.length > 0 ? (
        <div className="step-history-list">
          {history.map((step, i) => {
            const sub = step.reward_breakdown?.reflection_sub_scores || step.reflection_sub_scores || {};
            return (
            <div key={i} className="step-history-item">
              <div className={`step-history-number ${getStepClass(step, i)}`}>
                {step.step}
              </div>
              <div className="step-history-content">
                <div className="step-history-meta">
                  <span className="step-history-tests">
                    🧪 {step.tests_passed}/{step.tests_total}
                  </span>
                  <span className="step-history-reward">
                    ⭐ {(step.reward || step.combined_reward || 0).toFixed(3)}
                  </span>
                  {renderInterpretabilityBadge(step)}
                  {step.done && (
                    <span className="badge badge-easy">Done</span>
                  )}
                </div>
                {sub.s_bug !== undefined && (
                  <div className="step-history-subscores">
                    <span title="Bug Identification">Bug: {sub.s_bug.toFixed(2)} </span>
                    <span title="Fix Relevance">Fix: {sub.s_fix.toFixed(2)} </span>
                    <span title="Reasoning Consistency">Res: {sub.s_res.toFixed(2)}</span>
                  </div>
                )}
                <p className="step-history-hypothesis">
                  {step.hypothesis || 'No hypothesis'}
                </p>
              </div>
            </div>
            );
          })}
        </div>
      ) : (
        <div className="step-history-empty">
          No steps taken yet. Reset and submit fixes to build history.
        </div>
      )}
    </div>
  );
}
