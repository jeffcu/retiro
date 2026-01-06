import { useState, useEffect } from 'react';
import './PortfolioView.css';

const PortfolioSummary = ({ holdings, formatCurrency }) => {
    const totalMarketValue = holdings.reduce((sum, h) => sum + (h.market_value || 0), 0);
    const totalCostBasis = holdings.reduce((sum, h) => sum + (h.cost_basis || 0), 0);

    return (
        <div className="summary-container">
            <div className="summary-item">
                <span className="label">Total Holdings</span>
                <span className="value">{holdings.length}</span>
            </div>
            <div className="summary-item">
                <span className="label">Total Cost Basis</span>
                <span className="value">{formatCurrency(totalCostBasis)}</span>
            </div>
            <div className="summary-item">
                <span className="label">Total Market Value</span>
                <span className="value emphasis">{formatCurrency(totalMarketValue)}</span>
            </div>
        </div>
    );
};


const PortfolioView = () => {
    const [holdings, setHoldings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchHoldings = async () => {
            try {
                setLoading(true);
                const response = await fetch('/api/holdings');
                if (!response.ok) {
                    throw new Error(`HTTP Error: ${response.status}`);
                }
                const data = await response.json();
                setHoldings(data);
            } catch (e) {
                setError(e.message);
                console.error("Failed to fetch holdings:", e);
            } finally {
                setLoading(false);
            }
        };

        fetchHoldings();
    }, []);

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(value || 0);

    const totalMarketValue = holdings.reduce((sum, h) => sum + (h.market_value || 0), 0);

    if (loading) return <p>Loading portfolio...</p>;
    if (error) return <p>Error loading portfolio: {error}</p>;

    return (
        <div className="card">
            <h2>Holdings Overview</h2>
            <PortfolioSummary holdings={holdings} formatCurrency={formatCurrency} />
            {holdings.length > 0 ? (
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Account</th>
                                <th>Quantity</th>
                                <th>Cost Basis</th>
                                <th>Market Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {holdings.map(h => (
                                <tr key={h.holding_id}>
                                    <td>{h.symbol}</td>
                                    <td>{h.account_id}</td>
                                    <td>{h.quantity.toFixed(4)}</td>
                                    <td>{formatCurrency(h.cost_basis)}</td>
                                    <td>{formatCurrency(h.market_value)}</td>
                                </tr>
                            ))}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td colSpan="4">Total Market Value</td>
                                <td>{formatCurrency(totalMarketValue)}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            ) : (
                <p>No holdings data found. Please import a holdings CSV file via the 'Data & Settings' screen.</p>
            )}
        </div>
    );
};

export default PortfolioView;
