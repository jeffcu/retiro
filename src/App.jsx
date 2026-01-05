import { useState, useEffect } from 'react';
import SankeyChart from './SankeyChart';
import './App.css';

function App() {
  const [sankeyData, setSankeyData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch data from the backend API
    fetch('/api/sankey/income')
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // A valid Sankey chart needs at least one link.
        if (data && data.nodes && data.links && data.links.length > 0) {
          setSankeyData(data);
        } else {
          // Handle the case of no data or empty data gracefully
          setSankeyData({ nodes: [], links: [] });
        }
        setLoading(false);
      })
      .catch(error => {
        console.error("Error fetching Sankey data:", error);
        setError(error.message);
        setLoading(false);
      });
  }, []); // The empty dependency array means this effect runs once on mount

  return (
    <>
      <h1>Curie Trust Financial Control Center</h1>
      <div className="card">
        <h2>Income → Uses of Money</h2>
        {loading && <p>Loading chart data...</p>}
        {error && <p>Error loading data: {error}</p>}
        {sankeyData && sankeyData.links.length === 0 && !loading && (
            <p>No transaction data found. Please import a CSV file to see the chart.</p>
        )}
        {sankeyData && sankeyData.links.length > 0 && (
            <SankeyChart data={sankeyData} />
        )}
      </div>
    </>
  )
}

export default App
