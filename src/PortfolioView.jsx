import { useState, useEffect } from 'react';

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
    }).format(value);

    if (loading) return <p>Loading portfolio...</p>;
    if (error) return <p>Error loading portfolio: {error}</p>;

    return (
        <div className="portfolio-container">
            {holdings.length > 0 ? (
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Account</th>
                                <th>Quantity</th>
                                <th>Cost Basis</th>
                            </tr>
                        </thead>
                        <tbody>
                            {holdings.map(h => (
                                <tr key={h.holding_id}>
                                    <td>{h.symbol}</td>
                                    <td>{h.account_id}</td>
                                    <td>{h.quantity.toFixed(4)}</td>
                                    <td>{formatCurrency(h.cost_basis)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <p>No holdings data found. You may need to import a holdings CSV file.</p>
            )}
        </div>
    );
};

export default PortfolioView;
