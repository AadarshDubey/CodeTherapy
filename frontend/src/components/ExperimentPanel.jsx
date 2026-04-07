import React, { useState, useEffect } from 'react';
import useEnvironmentStore from '../store/useEnvironmentStore';
import ComparisonChart from './ComparisonChart';
import './ExperimentPanel.css';

const PHASE_LABELS = [
  '', // 0 = idle
  '⏳ Running...', // 1 = running
  '🔴 Blind Agent', // 2 = show blind results
  '🔀 Activate Reflection', // 3 = toggle
  '🟢 Reflection Agent', // 4 = show reflection results
  '📊 Final Results', // 5 = comparison chart
];

function getStepClass(step, allSteps) {
  if (step.done && step.tests_passed === step.tests_total) return 'success';
  if (allSteps.length > 1) {
    const idx = allSteps.indexOf(step);
    if (idx > 0 && step.tests_passed > allSteps[idx - 1].tests_passed) return 'improved';
  }
  return 'fail';
}

function getTestBadgeClass(step) {
  if (step.tests_passed === step.tests_total && step.tests_total > 0) return 'pass';
  if (step.tests_passed > 0) return 'partial';
  return 'fail';
}

function getScoreClass(val) {
  if (val >= 0.7) return 'good';
  if (val >= 0.4) return 'ok';
  return 'bad';
}

/** Render a timeline of agent steps */
function StepTimeline({ steps, mode }) {
  if (!steps || steps.length === 0) {
    return <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No steps recorded.</p>;
  }

  return (
    <div className="timeline-steps">
      {steps.map((step, i) => {
        const sub = step.reflection_sub_scores || {};
        return (
          <div key={i} className={`timeline-step ${getStepClass(step, steps)}`}>
            <div className="timeline-step-header">
              <span className="timeline-step-num">Step {step.step}</span>
              <span className={`timeline-step-tests ${getTestBadgeClass(step)}`}>
                🧪 {step.tests_passed}/{step.tests_total}
              </span>
              {step.reward !== undefined && (
                <span className="timeline-step-num">
                  ⭐ {step.reward.toFixed(3)}
                </span>
              )}
            </div>
            <div className="timeline-hypothesis">
              💡 {step.hypothesis || 'No hypothesis'}
            </div>
            <div className="timeline-scores">
              {sub.s_bug !== undefined && (
                <>
                  <span className={`timeline-score-pill ${getScoreClass(sub.s_bug)}`}>
                    Bug ID: {sub.s_bug.toFixed(2)}
                  </span>
                  <span className={`timeline-score-pill ${getScoreClass(sub.s_fix)}`}>
                    Fix: {sub.s_fix.toFixed(2)}
                  </span>
                  <span className={`timeline-score-pill ${getScoreClass(sub.s_res)}`}>
                    Reasoning: {sub.s_res.toFixed(2)}
                  </span>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function ExperimentPanel() {
  const experimentData = useEnvironmentStore((s) => s.experimentData);
  const isExperimentRunning = useEnvironmentStore((s) => s.isExperimentRunning);
  const experimentError = useEnvironmentStore((s) => s.experimentError);
  const experimentPhase = useEnvironmentStore((s) => s.experimentPhase);
  const setExperimentPhase = useEnvironmentStore((s) => s.setExperimentPhase);
  const runExperiment = useEnvironmentStore((s) => s.runExperiment);
  const clearExperiment = useEnvironmentStore((s) => s.clearExperiment);
  const selectedTask = useEnvironmentStore((s) => s.selectedTask);
  const tasks = useEnvironmentStore((s) => s.tasks);

  const [localTask, setLocalTask] = useState(selectedTask);
  const [toggleActive, setToggleActive] = useState(false);

  // Auto-advance toggle animation
  useEffect(() => {
    if (experimentPhase === 3) {
      const timer = setTimeout(() => setToggleActive(true), 800);
      return () => clearTimeout(timer);
    } else {
      setToggleActive(false);
    }
  }, [experimentPhase]);

  const handleRunExperiment = () => {
    const task = localTask === 'custom' ? selectedTask : localTask;
    runExperiment(task);
  };

  // Phases that are available based on current data
  const availablePhases = experimentData ? [2, 3, 4, 5] : [];

  const renderPhaseContent = () => {
    // Phase 0: Idle
    if (experimentPhase === 0 && !isExperimentRunning) {
      return (
        <div className="experiment-idle">
          <div className="experiment-idle-icon">🧪</div>
          <h3>A/B Experiment: Does Reflection Help?</h3>
          <p>
            Run the same debugging agent on the same task twice — once <strong style={{ color: '#f87171' }}>without</strong> reflection
            scoring (blind mode) and once <strong style={{ color: '#22d3ee' }}>with</strong> reflection scoring.
            See the dramatic difference in a story-driven demo.
          </p>
          <div className="experiment-idle-features">
            <div className="experiment-feature">📊 Success Rate Comparison</div>
            <div className="experiment-feature">📈 Step-by-Step Analysis</div>
            <div className="experiment-feature">🎯 Fix Quality Metrics</div>
          </div>
        </div>
      );
    }

    // Phase 1: Loading
    if (isExperimentRunning || experimentPhase === 1) {
      return (
        <div className="experiment-loading">
          <div className="experiment-spinner" />
          <div className="experiment-loading-text">
            Running A/B Experiment on <strong>{localTask}</strong>...
          </div>
          <div className="experiment-loading-subtext">
            Running blind mode, then reflection mode. This takes 60–90 seconds.
          </div>
        </div>
      );
    }

    // Error
    if (experimentError) {
      return (
        <div className="experiment-error">
          ⚠️ Experiment failed: {experimentError}
        </div>
      );
    }

    if (!experimentData) return null;

    // Phase 2: Blind Agent Steps
    if (experimentPhase === 2) {
      return (
        <div className="phase-content phase-timeline">
          <h3 className="blind-title">
            🔴 Blind Agent (No Reflection Scoring)
          </h3>
          <p style={{ color: '#94a3b8', marginBottom: '1rem', fontSize: '0.85rem' }}>
            The agent gets the same LLM, same prompt, same code — but receives <strong>no feedback</strong> on
            reflection quality. Watch how hypotheses stay vague and fixes are untargeted.
          </p>
          <p style={{ fontSize: '0.8rem', marginBottom: '1rem' }}>
            <span style={{ color: experimentData.blind.success ? '#4ade80' : '#fb7185' }}>
              {experimentData.blind.success ? '✅ Succeeded' : '❌ Failed'} in {experimentData.blind.steps_taken} steps
            </span>
            {' · '}
            Tests: {experimentData.blind.final_tests_passed}/{experimentData.blind.final_tests_total}
          </p>
          <StepTimeline steps={experimentData.blind.steps} mode="blind" />
        </div>
      );
    }

    // Phase 3: Toggle Animation
    if (experimentPhase === 3) {
      return (
        <div className="phase-content phase-toggle">
          <div
            className={`toggle-animation ${toggleActive ? 'active' : ''}`}
            onClick={() => setToggleActive(!toggleActive)}
          >
            <div className="toggle-knob">
              {toggleActive ? '🧠' : '🚫'}
            </div>
          </div>
          <h3 style={{ color: toggleActive ? '#22d3ee' : '#f87171' }}>
            {toggleActive
              ? '✨ Reflection System: ACTIVATED'
              : '🚫 Reflection System: OFF'}
          </h3>
          <p>
            {toggleActive
              ? 'Now the LLM-as-a-Judge scores every hypothesis, fix, and reasoning chain. Watch how targeted debugging becomes.'
              : 'Click the toggle or proceed to see what happens when we turn on process supervision.'}
          </p>
        </div>
      );
    }

    // Phase 4: Reflection Agent Steps
    if (experimentPhase === 4) {
      return (
        <div className="phase-content phase-timeline">
          <h3 className="reflection-title">
            🟢 Reflection Agent (LLM-as-a-Judge Scoring)
          </h3>
          <p style={{ color: '#94a3b8', marginBottom: '1rem', fontSize: '0.85rem' }}>
            Same agent, same task — but now reflection quality is scored. Watch how hypotheses
            become <strong>precise</strong> and fixes become <strong>targeted</strong>.
          </p>
          <p style={{ fontSize: '0.8rem', marginBottom: '1rem' }}>
            <span style={{ color: experimentData.reflection.success ? '#4ade80' : '#fb7185' }}>
              {experimentData.reflection.success ? '✅ Succeeded' : '❌ Failed'} in {experimentData.reflection.steps_taken} steps
            </span>
            {' · '}
            Tests: {experimentData.reflection.final_tests_passed}/{experimentData.reflection.final_tests_total}
          </p>
          <StepTimeline steps={experimentData.reflection.steps} mode="reflection" />
        </div>
      );
    }

    // Phase 5: Final Comparison
    if (experimentPhase === 5) {
      return (
        <div className="phase-content phase-results">
          <ComparisonChart comparison={experimentData.comparison} />
        </div>
      );
    }

    return null;
  };

  return (
    <div className="glass-panel experiment-panel" id="experiment-panel">
      <div className="experiment-header">
        <div className="experiment-title">
          <span>🧪</span> A/B Experiment — Reflection Impact Demo
        </div>
        <div className="experiment-controls">
          <select
            className="experiment-task-select"
            value={localTask}
            onChange={(e) => setLocalTask(e.target.value)}
            disabled={isExperimentRunning}
          >
            {tasks.length > 0 ? (
              tasks.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name} ({t.difficulty})
                </option>
              ))
            ) : (
              <>
                <option value="api_json_fix">api_json_fix (easy)</option>
                <option value="csv_processor_fix">csv_processor_fix (medium)</option>
                <option value="retry_decorator_fix">retry_decorator_fix (hard)</option>
              </>
            )}
          </select>
          <button
            className="btn-primary"
            onClick={handleRunExperiment}
            disabled={isExperimentRunning}
            id="btn-run-experiment"
          >
            {isExperimentRunning ? '⟳ Running...' : '🚀 Run A/B Experiment'}
          </button>
          {experimentData && (
            <button
              className="btn-secondary"
              onClick={clearExperiment}
              id="btn-clear-experiment"
            >
              🔄 Reset
            </button>
          )}
        </div>
      </div>

      {/* Story phase navigation */}
      {experimentData && experimentPhase >= 2 && (
        <div className="story-phases">
          {[
            { phase: 2, label: '🔴 Blind Agent' },
            { phase: 3, label: '🔀 Toggle' },
            { phase: 4, label: '🟢 Reflection Agent' },
            { phase: 5, label: '📊 Results' },
          ].map(({ phase, label }) => (
            <button
              key={phase}
              className={`story-phase-btn ${experimentPhase === phase ? 'active' : ''} ${
                experimentPhase > phase ? 'completed' : ''
              }`}
              onClick={() => setExperimentPhase(phase)}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {renderPhaseContent()}
    </div>
  );
}
