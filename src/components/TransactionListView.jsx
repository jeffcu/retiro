import { useState, useEffect } from 'react';
import './TransactionListView.css';
import FilterPanel from './FilterPanel';
import BarChart from './BarChart';
import RuleCreator from './RuleCreator';

const filterConfig = [
    { id: 'category', label: 'Category', type: 'select', optionsKey: 'categories' },
    { id: 'account_id', label: 'Account', type: 'select', optionsKey: 'accounts' },
    { id: 'institution', label: 'Institution', type: 'select', optionsKey: 'institutions' },
    { id: 'cashflow_type', label: 'Cashflow Type', type: 'select', optionsKey: 'cashflowTypes' },
    { id: 'description', label: 'Description Contains', type: 'text', placeholder: 'e.g., Amazon' },
    { id: 'tags', label: 'Tag Contains', type: 'text', placeholder: 'e.g., vacation' },
];

const RulePromptCard = ({ onShowCreator }) => {
    return (
        <div className="rule-prompt-card">
            <p>Want to automate this? Create a rule from these filters.</p>
            <button onClick={onShowCreator}>Create Rule</button>
        </div>
    );
};

const TransactionListView = () => {
    const [transactions, setTransactions] = useState([]);
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeFilters, setActiveFilters] = useState({});
    const [showRuleCreator, setShowRuleCreator] = useState(false);

    const fetchData = async (filters = {}) => {
        try {
            setLoading(true);
            setActiveFilters(filters);
            setShowRuleCreator(false); // Hide creator on new filter/fetch
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

    const handleRuleSave = async () => {
        setShowRuleCreator(false);
        try {
            // Re-categorize everything with the new rule
            const recategorizeRes = await fetch('/api/transactions/recategorize', { method: 'POST' });
            if (!recategorizeRes.ok) throw new Error('Recategorization failed');
            
            const result = await recategorizeRes.json();
            alert(result.message); // Inform the user

            // Re-fetch the data to show the updated view
            await fetchData(activeFilters);

        } catch (err) {
            alert(`Error after saving rule: ${err.message}`);
        }
    };

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

    const hasActiveFilters = Object.keys(activeFilters).length > 0;

    if (error) return <p>Error loading transactions: {error}</p>;

    return (
        <>
            <FilterPanel config={filterConfig} onFilterSubmit={fetchData} />

            {showRuleCreator ? (
                <RuleCreator 
                    filters={activeFilters}
                    onSave={handleRuleSave}
                    onCancel={() => setShowRuleCreator(false)}
                />
            ) : hasActiveFilters && transactions.length > 0 && (
                <RulePromptCard onShowCreator={() => setShowRuleCreator(true)} />
            )}

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
                                    <th>Cashflow Type</th>
                                    <th>Category</th>
                                    <th>Tags</th>
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
                                        <td>{t.cashflow_type}</td>
                                        <td>{t.category}</td>
                                        <td>{t.tags}</td>
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
