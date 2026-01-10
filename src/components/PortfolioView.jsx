import { useState, useEffect, useMemo } from 'react';
import './PortfolioView.css';
import FilterPanel from './FilterPanel';
import BarChart from './BarChart';
import TimeFilter from './TimeFilter';

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

const filterConfig = [
    { id: 'account_id', label: 'Account', type: 'select', optionsKey: 'accounts' },
    { id: 'symbol', label: 'Symbol', type: 'text', placeholder: 'e.g., AAPL' },
];

const PortfolioView = () => {
    const [holdings, setHoldings] = useState([]);
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeFilters, setActiveFilters] = useState({ period: 'all' });
    const [sortConfig, setSortConfig] = useState(null);

    const fetchData = async (filters = activeFilters) => {
        try {
            setLoading(true);
            setActiveFilters(filters);
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

    const sortedHoldings = useMemo(() => {
        let sortableItems = [...holdings];
        if (sortConfig !== null) {
            sortableItems.sort((a, b) => {
                const valA = a[sortConfig.key];
                const valB = b[sortConfig.key];
    
                if (valA === null || valA === undefined) return 1;
                if (valB === null || valB === undefined) return -1;
                
                if (valA < valB) {
                    return sortConfig.direction === 'ascending' ? -1 : 1;
                }
                if (valA > valB) {
                    return sortConfig.direction === 'ascending' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortableItems;
    }, [holdings, sortConfig]);

    const requestSort = (key) => {
        let direction = 'descending';
        if (sortConfig && sortConfig.key === key && sortConfig.direction === 'descending') {
            direction = 'ascending';
        } else if (sortConfig && sortConfig.key === key && sortConfig.direction === 'ascending') {
            setSortConfig(null);
            return;
        }
        setSortConfig({ key, direction });
    };

    const getSortIndicator = (key) => {
        if (!sortConfig || sortConfig.key !== key) return null;
        return sortConfig.direction === 'ascending' ? '▲' : '▼';
    };

    const handlePanelFilterSubmit = (panelFilters) => {
        const newFilters = { ...panelFilters, period: activeFilters.period };
        fetchData(newFilters);
    };

    const handlePeriodChange = (period) => {
        const newFilters = { ...activeFilters, period };
        fetchData(newFilters);
    };

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value || 0);

    const totalMarketValue = holdings.reduce((sum, h) => sum + (h.market_value || 0), 0);

    if (error) return <p>Error loading portfolio: {error}</p>;

    return (
        <>
            <FilterPanel config={filterConfig} onFilterSubmit={handlePanelFilterSubmit} />

            <div className="card">
                <div className="chart-header">
                    <h2>Filtered Results Summary</h2>
                    <TimeFilter 
                        selectedPeriod={activeFilters.period || 'all'} 
                        onPeriodChange={handlePeriodChange} 
                    />
                </div>
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
                                            <th className="sortable" onClick={() => requestSort('symbol')}>
                                                Symbol <span className="sort-indicator">{getSortIndicator('symbol')}</span>
                                            </th>
                                            <th className="sortable" onClick={() => requestSort('account_id')}>
                                                Account <span className="sort-indicator">{getSortIndicator('account_id')}</span>
                                            </th>
                                            <th className="sortable" onClick={() => requestSort('quantity')}>
                                                Quantity <span className="sort-indicator">{getSortIndicator('quantity')}</span>
                                            </th>
                                            <th className="sortable" onClick={() => requestSort('cost_basis')}>
                                                Cost Basis <span className="sort-indicator">{getSortIndicator('cost_basis')}</span>
                                            </th>
                                            <th className="sortable" onClick={() => requestSort('market_value')}>
                                                Market Value <span className="sort-indicator">{getSortIndicator('market_value')}</span>
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {sortedHoldings.map(h => (
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
