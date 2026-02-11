import { useState, useEffect } from 'react';
import './LayeredReturnsSummary.css';
import { useMode } from '../context/ModeContext';
import SankeyChart from '../SankeyChart';

const MetricDisplay = ({ label, value }) => (
    <div className="metric-item">
        <span className="metric-label">{label}</span>
        <span className="metric-value">{value.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 })}</span>
    </div>
);

const LayeredReturnsSummary = () => {
    const { mode } = useMode(); // Although not used in this component, it's good practice to keep for future demo logic
    const [summary, setSummary] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                setIsLoading(true);
                setError(null);
                const response = await fetch(`/api/portfolio/layered-returns-summary`);
                if (!response.ok) {
                    throw new Error('Failed to fetch layered returns summary');
                }
                const data = await response.json();
                setSummary(data);
            } catch (err) {
                setError(err.message);
                console.error(err);
            } finally {
                setIsLoading(false);
            }
        };

        fetchSummary();
    }, [mode]);

    if (isLoading) {
        return <div className="card layered-returns-card"><h2>Layered Returns</h2><p>Calculating summary...</p></div>;
    }

    if (error) {
        return <div className="card layered-returns-card error"><h2>Layered Returns</h2><p>Error calculating summary: {error}</p></div>;
    }
    
    if (!summary || !summary.sankey_data || summary.sankey_data.links.length === 0) {
        return (
            <div className="card layered-returns-card">
                <h2>Layered Returns (Since Inception)</h2>
                <p style={{ textAlign: 'center', padding: '2rem 0' }}>
                    Not enough data to calculate returns. Ensure portfolio cost basis and market value are available.
                </p>
            </div>
        );
    }

    const { metrics, sankey_data, notes } = summary;
    const total_leakage = metrics.total_fees + metrics.estimated_taxes;

    return (
        <div className="card layered-returns-card">
            <h2>Layered Returns (Since Inception)</h2>
            <div className="metrics-container">
                <MetricDisplay label="Gross Return" value={metrics.gross_return} />
                <div className="metric-operator">−</div>
                <MetricDisplay label="Total Leakage (Fees + Taxes)" value={total_leakage} />
                <div className="metric-operator">=</div>
                <MetricDisplay label="After-Tax Return" value={metrics.after_tax_return} />
            </div>
            <div className="sankey-container-card">
                <SankeyChart data={sankey_data} />
            </div>
            <p className="summary-notes"><em>{notes}</em></p>
        </div>
    );
};

export default LayeredReturnsSummary;
