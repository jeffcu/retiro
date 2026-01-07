import { useState, useEffect } from 'react';
import './PortfolioView.css';
import FilterPanel from './components/FilterPanel';
import BarChart from './components/BarChart';

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
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const filterConfig = [
        { id: 'account_id', label: 'Account', type: 'select', optionsKey: 'accounts' },
        { id: 'symbol', label: 'Symbol', type: 'text', placeholder: 'e.g., AAPL' },
    ];

    const fetchData = async (filters = {}) => {
        try {
            setLoading(true);
            const query = new URLSearchParams(filters).toString();

            const [holdingsRes, chartRes] = await Promise.all([
                fetch(`/api/holdings?${query}`),
                fetch(`/api/analysis/portfolio-chart?${query}`)
            ]);

            if (!holdingsRes.ok) throw new Error(`HTTP Error (Holdings): ${holdingsRes.status}`);
            if (!chartRes.ok) throw new Error(`HTTP Error (Chart): ${chartRes.status}`);

            const holdingsData = await holdingsRes.json();
            const chartData = await chartRes.json();

            setHoldings(holdingsData);
            setChartData(chartData);
        } catch (e) {
            setError(e.message);
            console.error("Failed to fetch portfolio data:", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(value || 0);

    const totalMarketValue = holdings.reduce((sum, h) => sum + (h.market_value || 0), 0);

    if (error) return <p>Error loading portfolio: {error}</p>;

    return (
        <>
            <FilterPanel config={filterConfig} onFilterSubmit={fetchData} />

            <div className="card">
                <h2>Filtered Results Summary</h2>
                {loading ? (
                    <p>Loading chart...</p>
                ) : chartData.length > 0 ? (
                    <BarChart 
                        data={chartData}
                        indexBy="id"
                        keys={['value']}
                        axisLeftLabel="Market Value"
                        axisBottomLabel="Symbol"
                    />
                ) : (
                    <p>No data matches the current filters.</p>
                )}
            </div>

            <div className="card">
                <h2>Holdings Details</h2>
                {loading ? (
                    <p>Loading holdings...</p>
                ) : (
                    <>
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
                            <p>No holdings data found for the current filter. Please import a holdings CSV file or adjust filters.</p>
                        )}
                    </>
                )}
            </div>
        </>
    );
};

export default PortfolioView;
