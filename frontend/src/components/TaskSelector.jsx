import React, { useEffect } from 'react';
import useEnvironmentStore from '../store/useEnvironmentStore';
import './TaskSelector.css';

const DIFFICULTY_MAP = {
  api_json_fix: { label: '🟩 Easy', class: 'badge-easy' },
  csv_processor_fix: { label: '🟨 Medium', class: 'badge-medium' },
  retry_decorator_fix: { label: '🟥 Hard', class: 'badge-hard' },
};

const DESCRIPTIONS = {
  api_json_fix: 'Fix an api JSON parsing logic. Evaluates basic generalization.',
  csv_processor_fix: 'Fix row offset and stream bugs in CSV parser. Evaluates multi-step logic.',
  retry_decorator_fix: 'Fix complex state leaking in async retry decorator. Evaluates hard bug scaling.',
};

export default function TaskSelector() {
  const tasks = useEnvironmentStore((s) => s.tasks);
  const selectedTask = useEnvironmentStore((s) => s.selectedTask);
  const selectTask = useEnvironmentStore((s) => s.selectTask);
  const fetchTasks = useEnvironmentStore((s) => s.fetchTasks);

  const customBuggyCode = useEnvironmentStore((s) => s.customBuggyCode);
  const customTestCode = useEnvironmentStore((s) => s.customTestCode);
  const setCustomCode = useEnvironmentStore((s) => s.setCustomCode);

  useEffect(() => {
    fetchTasks();
  }, []);

  const difficulty = DIFFICULTY_MAP[selectedTask] || { label: '❓ Unknown', class: '' };

  return (
    <div className="glass-panel task-selector" id="task-selector">
      <label className="task-selector-label" htmlFor="task-dropdown">
        Select Task (Generalization Matrix)
      </label>
      <select
        id="task-dropdown"
        className="task-selector-dropdown"
        value={selectedTask}
        onChange={(e) => selectTask(e.target.value)}
      >
        {tasks.length > 0 ? (
          <>
            {tasks.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name} ({t.difficulty})
              </option>
            ))}
            <option value="custom">Custom Task (Playground)</option>
          </>
        ) : (
          <>
            <option value="api_json_fix">api_json_fix (easy)</option>
            <option value="csv_processor_fix">csv_processor_fix (medium)</option>
            <option value="retry_decorator_fix">retry_decorator_fix (hard)</option>
            <option value="custom">custom (playground)</option>
          </>
        )}
      </select>
      
      {selectedTask === 'custom' ? (
        <div className="task-selector-custom">
          <div style={{ marginTop: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.9rem', marginBottom: '0.5rem', color: '#ffb86c' }}>
              Buggy Code Snippet
            </label>
            <textarea
              style={{ width: '100%', minHeight: '120px', backgroundColor: '#1e1e2e', color: '#fff', padding: '0.5rem', fontFamily: 'monospace', border: '1px solid #444', borderRadius: '4px' }}
              value={customBuggyCode}
              onChange={(e) => setCustomCode(e.target.value, customTestCode)}
              placeholder="def example():\n    return 1"
            />
          </div>
          <div style={{ marginTop: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.9rem', marginBottom: '0.5rem', color: '#ffb86c' }}>
              Test Cases (Standard Python asserts)
            </label>
            <textarea
              style={{ width: '100%', minHeight: '80px', backgroundColor: '#1e1e2e', color: '#fff', padding: '0.5rem', fontFamily: 'monospace', border: '1px solid #444', borderRadius: '4px' }}
              value={customTestCode}
              onChange={(e) => setCustomCode(customBuggyCode, e.target.value)}
              placeholder="assert example() == 2"
            />
          </div>
        </div>
      ) : (
        <div className="task-selector-info">
          <div className="task-selector-difficulty">
            <span className={`badge ${difficulty.class}`}>{difficulty.label}</span>
          </div>
          <p>{DESCRIPTIONS[selectedTask] || 'Select a task to see details.'}</p>
        </div>
      )}
    </div>
  );
}
