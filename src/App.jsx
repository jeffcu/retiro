import { useState, useEffect, useCallback } from 'react';
import SankeyChart from './SankeyChart';
import TransactionTable from './TransactionTable';
import RulesManager from './RulesManager';
import PortfolioView from './PortfolioView';
import './App.css';
import './TransactionTable.css';
import './RulesManager.css';
import './PortfolioView.css';

function App() {
  const [sankeyData, setSankeyData] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [showTable, setShowTable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Using useCallback to memoize the fetch function so it can be passed as a prop
  // without causing unnecessary re-renders in the child component (RulesManager).
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch both data sets in parallel
      const [sankeyResponse, transactionsResponse] = await Promise.all([
        fetch('/api/sankey/income'),
        fetch('/api/transactions')
      ]);

      if (!sankeyResponse.ok) throw new Error(`HTTP error (Sankey)! status: ${sankeyResponse.status}`);
      if (!transactionsResponse.ok) throw new Error(`HTTP error (Transactions)! status: ${transactionsResponse.status}`);
      
      const sankeyJson = await sankeyResponse.json();
      const transactionsJson = await transactionsResponse.json();

      setSankeyData(sankeyJson);
      setTransactions(transactionsJson);

    } catch (e) {
      console.error("Error fetching data:", e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []); // Empty dependency array means this function is created once.

  // Initial data fetch on component mount
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const isChartVisible = sankeyData && sankeyData.links && sankeyData.links.length > 0;

  return (
    <>
      <h1>Curie Trust Financial Control Center</h1>
      
      <div className="card">
        <h2>Income → Uses of Money</h2>
        {loading && <p>Loading chart data...</p>}
        {error && <p>Error loading data: {error}</p>}
        
        {isChartVisible ? (
            <SankeyChart data={sankeyData} />
        ) : (
          !loading && <p>No transaction data found. Please import a CSV file and refresh the page.</p>
        )}
      </div>

      <div className="card">
        <h2>Portfolio Holdings</h2>
        <PortfolioView />
      </div>

      <div className="card">
        <h2>Categorization Rules Management</h2>
        <p>Define rules to automatically categorize transactions during import.</p>
        <RulesManager onRuleAdded={fetchData} />
      </div>

      <div className="card">
          <h2>Diagnostic Data Viewer</h2>
          <button onClick={() => setShowTable(!showTable)} style={{marginBottom: '1rem'}}>
              {showTable ? 'Hide' : 'Show'} Raw Transaction Data
          </button>
          {showTable && <TransactionTable transactions={transactions} />}
      </div>
    </>
  )
}

export default App;
