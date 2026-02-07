import { useState, useEffect } from 'react';
import './LayeredReturnsSummary.css';
import { useMode } from '../context/ModeContext';

const MetricDisplay = ({ label, value, isPercent = false }) => (
    <div className="metric-item">
        <span className="metric-label">{label}</span>
        <span className="metric-value">{isPercent ? `${value.toFixed(2)}%` : value.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 })}</span>
    </div>
);

const PortfolioGainsSummary = () => {
    const { mode } = useMode();
    const [summary, setSummary] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                setIsLoading(true);
                setError(null);
                const response = await fetch(`/api/portfolio/overall-return?mode=${mode}`);
                if (!response.ok) {
                    throw new Error('Failed to fetch portfolio summary data');
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
        return <div className="card"><p>Calculating summary...</p></div>;
    }

    if (error) {
        return <div className="card error"><p>Error calculating summary: {error}</p></div>;
    }
    
    if (!summary) return null;

    return (
        <div className="card layered-returns-card">
            <h2>Portfolio Gains (Since Inception)</h2>
            <div className="metrics-container">
                <MetricDisplay label="Total Assets (Market Value)" value={summary.total_market_value} />
                <div className="metric-operator">−</div>
                <MetricDisplay label="Total Basis" value={summary.total_cost_basis} />
                <div className="metric-operator">=</div>
                <MetricDisplay label="Total Gains" value={summary.total_gain_dollars} />
                <MetricDisplay label="Increase" value={summary.total_gain_percent} isPercent={true} />
            </div>
            <p className="summary-notes"><em>Note: {summary.notes}</em></p>
        </div>
    );
};

export default PortfolioGainsSummary;
