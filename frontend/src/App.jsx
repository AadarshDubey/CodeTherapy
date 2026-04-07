import React from 'react';
import Header from './components/Header';
import TaskSelector from './components/TaskSelector';
import ActionPanel from './components/ActionPanel';
import CodeViewer from './components/CodeViewer';
import TestResults from './components/TestResults';
import ReflectionPanel from './components/ReflectionPanel';
import RewardMeter from './components/RewardMeter';
import RewardChart from './components/RewardChart';
import StepHistory from './components/StepHistory';
import LearningCurve from './components/LearningCurve';
import ExperimentPanel from './components/ExperimentPanel';
import useEnvironmentStore from './store/useEnvironmentStore';
import './App.css';

export default function App() {
  const activeView = useEnvironmentStore((s) => s.activeView);
  const setActiveView = useEnvironmentStore((s) => s.setActiveView);

  return (
    <div className="app" id="app">
      <Header />

      {/* View Tabs */}
      <div className="view-tabs">
        <button
          className={`view-tab ${activeView === 'agent' ? 'active' : ''}`}
          onClick={() => setActiveView('agent')}
          id="tab-agent"
        >
          <span className="view-tab-icon">🤖</span>
          Live Agent
        </button>
        <button
          className={`view-tab ${activeView === 'experiment' ? 'active' : ''}`}
          onClick={() => setActiveView('experiment')}
          id="tab-experiment"
        >
          <span className="view-tab-icon">🧪</span>
          A/B Experiment
          <span className="view-tab-badge">NEW</span>
        </button>
      </div>

      <main className="app-main">
        {activeView === 'agent' ? (
          <>
            {/* Top bar: Task Selector + Action Panel */}
            <div className="app-top-bar">
              <TaskSelector />
              <ActionPanel />
            </div>

            {/* Two-column layout */}
            <div className="app-grid">
              {/* Left column: Code + Tests */}
              <div className="app-col-left">
                <CodeViewer />
                <TestResults />
              </div>

              {/* Right column: Reflection + Rewards + History */}
              <div className="app-col-right">
                <LearningCurve />
                <ReflectionPanel />
                <div className="reward-row">
                  <RewardMeter />
                  <RewardChart />
                </div>
                <StepHistory />
              </div>
            </div>
          </>
        ) : (
          <ExperimentPanel />
        )}
      </main>
    </div>
  );
}
