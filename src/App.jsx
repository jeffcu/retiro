import { useState } from 'react';
import SideBar from './components/SideBar';
import HomeView from './components/HomeView';
import PortfolioView from './components/PortfolioView';
import DataImportView from './components/DataImportView';
import PlaceholderView from './components/PlaceholderView';
import TransactionListView from './components/TransactionListView';
import RealEstateView from './components/RealEstateView'; // IMPORTED
import ErrorBoundary from './components/ErrorBoundary'; 
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
        return <TransactionListView key={JSON.stringify(params)} initialFilters={params} />;
      case 'Real Estate':
        return <RealEstateView />; // ACTIVATED
      case 'Projects/Tags':
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
        <ErrorBoundary>
          {renderView()}
        </ErrorBoundary>
      </main>
    </>
  );
}

export default App;
