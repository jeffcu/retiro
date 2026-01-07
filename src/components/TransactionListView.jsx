import { useState, useEffect, useMemo } from 'react';
import './TransactionListView.css';
import FilterPanel from './FilterPanel';
import BarChart from './BarChart';

const TransactionListView = () => {
    const [transactions, setTransactions] = useState([]);
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const filterConfig = [
        { id: 'category', label: 'Category', type: 'select', optionsKey: 'categories' },
        { id: 'account_id', label: 'Account', type: 'select', optionsKey: 'accounts' },
        { id: 'institution', label: 'Institution', type: 'select', optionsKey: 'institutions' },
        { id: 'description', label: 'Description Contains', type: 'text', placeholder: 'e.g., Amazon' },
        { id: 'tags', label: 'Tag Contains', type: 'text', placeholder: 'e.g., vacation' },
    ];

    const fetchData = async (filters = {}) => {
        try {
            setLoading(true);
            const query = new URLSearchParams(filters).toString();

            const [transactionsRes, chartRes] = await Promise.all([
                fetch(`/api/transactions?${query}`),
                fetch(`/api/analysis/cashflow-chart?${query}`)
            ]);

            if (!transactionsRes.ok) throw new Error(`HTTP Error (Transactions): ${transactionsRes.status}`);
            if (!chartRes.ok) throw new Error(`HTTP Error (Chart): ${chartRes.status}`);

            const transactionsData = await transactionsRes.json();
            const chartData = await chartRes.json();

            setTransactions(transactionsData);
            setChartData(chartData);
        } catch (e) {
            setError(e.message);
            console.error("Failed to fetch transaction data:", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData(); // Initial fetch with no filters
    }, []);

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value || 0);

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString();
    }

    if (error) return <p>Error loading transactions: {error}</p>;

    return (
        <>
            <FilterPanel config={filterConfig} onFilterSubmit={fetchData} />

            <div className="card">
                <h2>Monthly Summary</h2>
                {loading ? (
                    <p>Loading chart...</p>
                ) : chartData.length > 0 ? (
                    <BarChart 
                        data={chartData}
                        indexBy="month"
                        keys={['Income', 'Expense']}
                        axisLeftLabel="Amount ($)"
                        axisBottomLabel="Month"
                    />
                ) : (
                    <p>No data available for chart with current filters.</p>
                )}
            </div>

            <div className="card">
                <h2>Transaction Details</h2>
                {loading ? (
                    <p>Loading transactions...</p>
                ) : transactions.length > 0 ? (
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Account</th>
                                    <th>Institution</th>
                                    <th>Description</th>
                                    <th>Category</th>
                                    <th style={{ textAlign: 'right' }}>Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                                {transactions.map(t => (
                                    <tr key={t.transaction_id}>
                                        <td>{formatDate(t.transaction_date)}</td>
                                        <td>{t.account_id}</td>
                                        <td>{t.institution}</td>
                                        <td>{t.description}</td>
                                        <td>{t.category}</td>
                                        <td style={{ color: t.amount > 0 ? 'var(--gold-accent)' : 'inherit' }}>
                                            {formatCurrency(t.amount)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p>No transactions found for the current filter. Please import a transaction CSV file or adjust filters.</p>
                )}
            </div>
        </>
    );
};

export default TransactionListView;
