import { useState } from 'react';
import NavBar from './components/NavBar';
import HomeView from './components/HomeView';
import PortfolioView from './PortfolioView'; // Corrected Path
import DataImportView from './components/DataImportView';
import PlaceholderView from './components/PlaceholderView';
import TransactionListView from './components/TransactionListView';
import './App.css';

function App() {
  const [activeView, setActiveView] = useState('Home');

  const renderView = () => {
    switch (activeView) {
      case 'Home':
        return <HomeView />;
      case 'Portfolio':
        return <PortfolioView />;
      case 'Data & Settings':
        return <DataImportView />;
      case 'Cashflow':
        return <TransactionListView />;
      case 'Projects/Tags':
      case 'Real Estate':
      case 'Forecast':
        return <PlaceholderView viewName={activeView} />;
      default:
        return <HomeView />;
    }
  };

  return (
    <>
      <NavBar activeView={activeView} setActiveView={setActiveView} />
      <main className="main-content">
        <h1>{activeView}</h1>
        {renderView()}
      </main>
    </>
  );
}

export default App;
