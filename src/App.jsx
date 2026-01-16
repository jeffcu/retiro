import { useState } from 'react';
import SideBar from './components/SideBar';
import HomeView from './components/HomeView';
import PortfolioView from './components/PortfolioView';
import DataImportView from './components/DataImportView';
import PlaceholderView from './components/PlaceholderView';
import TransactionListView from './components/TransactionListView';
import ErrorBoundary from './components/ErrorBoundary'; // ADDED: Diagnostic component
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState({ name: 'Home', params: {} });

  const navigateTo = (viewName, params = {}) => {
    setCurrentView({ name: viewName, params });
  };

  const setActiveView = (viewName) => {
    navigateTo(viewName);
  };

  const renderView = () => {
    const { name, params } = currentView;
    switch (name) {
      case 'Home':
        return <HomeView navigateTo={navigateTo} />;
      case 'Portfolio':
        return <PortfolioView />;
      case 'Data & Settings':
        return <DataImportView />;
      case 'Cashflow':
        // Using a key forces React to remount the component when params change,
        // ensuring a fresh state for the new drill-down view.
        return <TransactionListView key={JSON.stringify(params)} initialFilters={params} />;
      case 'Projects/Tags':
      case 'Real Estate':
      case 'Forecast':
        return <PlaceholderView viewName={name} />;
      default:
        return <HomeView navigateTo={navigateTo} />;
    }
  };

  return (
    <>
      <SideBar activeView={currentView.name} setActiveView={setActiveView} />
      <main className="main-content">
        <h1>{currentView.name}</h1>
        <ErrorBoundary> {/* WRAPPED: Catches rendering errors */}
          {renderView()}
        </ErrorBoundary>
      </main>
    </>
  );
}

export default App;
