import { useState, useEffect } from 'react';
import './LayeredReturnsSummary.css';

const MetricDisplay = ({ label, value, note, isPercent = false }) => (
    <div className="metric-item">
        <span className="metric-label">{label}</span>
        <span className="metric-value">{isPercent ? `${value.toFixed(2)}%` : value.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 })}</span>
        {note && <span className="metric-note">{note}</span>}
    </div>
);

const LayeredReturnsSummary = ({ period }) => {
    const [returns, setReturns] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchReturns = async () => {
            try {
                setIsLoading(true);
                setError(null);
                const response = await fetch(`/api/portfolio/layered-returns?period=${period}`);
                if (!response.ok) {
                    throw new Error('Failed to fetch layered returns data');
                }
                const data = await response.json();
                setReturns(data);
            } catch (err) {
                setError(err.message);
                console.error(err);
            } finally {
                setIsLoading(false);
            }
        };

        fetchReturns();
    }, [period]);

    if (isLoading) {
        return <div className="card"><p>Calculating returns...</p></div>;
    }

    if (error) {
        return <div className="card error"><p>Error calculating returns: {error}</p></div>;
    }
    
    if (!returns) return null;

    return (
        <div className="card layered-returns-card">
            <h2>Portfolio Return (Approximated)</h2>
            <div className="metrics-container">
                <MetricDisplay label="Gross Return" value={returns.gross_return_percent} isPercent={true} note={`$${returns.gross_return_dollars.toLocaleString()}`} />
                <div className="metric-operator">−</div>
                <MetricDisplay label="Fees (Period)" value={returns.fees_dollars} note={` `} />
                <div className="metric-operator">=</div>
                <MetricDisplay label="After Fees" value={returns.after_fees_return_percent} isPercent={true} note={`$${returns.after_fees_return_dollars.toLocaleString()}`} />
                <div className="metric-operator">−</div>
                <MetricDisplay label="Taxes (Est. on Yield)" value={returns.taxes_dollars} note={` `} />
                <div className="metric-operator">=</div>
                <MetricDisplay label="After-Tax Return" value={returns.after_taxes_return_percent} isPercent={true} note={`$${returns.after_taxes_return_dollars.toLocaleString()}`} />
            </div>
            <p className="summary-notes"><em>Note: {returns.notes}</em></p>
        </div>
    );
};

export default LayeredReturnsSummary;
