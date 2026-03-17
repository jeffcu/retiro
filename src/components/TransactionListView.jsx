import { useState, useEffect, useMemo } from 'react';
import './TransactionListView.css';
import FilterPanel from './FilterPanel';
import BarChart from './BarChart';
import RuleCreator from './RuleCreator';
import TransactionEditorModal from './TransactionEditorModal';
import TimeFilter from './TimeFilter';

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

const TransactionListView = ({ initialFilters = {} }) => {
    const [transactions, setTransactions] = useState([]);
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeFilters, setActiveFilters] = useState({ period: 'all', ...initialFilters });
    const [showRuleCreator, setShowRuleCreator] = useState(false);
    const [editingTransaction, setEditingTransaction] = useState(null);
    const [sortConfig, setSortConfig] = useState(null);
    
    // Bulk Tagging State
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [bulkTagInput, setBulkTagInput] = useState('');
    const [isBulkTagging, setIsBulkTagging] = useState(false);

    const fetchData = async (filters = activeFilters) => {
        try {
            setLoading(true);
            setActiveFilters(filters);
            setShowRuleCreator(false); // Hide creator on new filter/fetch
            setSelectedIds(new Set()); // Clear selection on data change
            
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
        fetchData(activeFilters); // Initial fetch with filters from props/state
    }, []); // This effect runs only once on mount due to the key prop in App.jsx

    const sortedTransactions = useMemo(() => {
        let sortableItems = [...transactions];
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
    }, [transactions, sortConfig]);

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

    const handleTransactionSave = () => {
        setEditingTransaction(null); // Close the modal
        fetchData(activeFilters); // Refresh the data
    };

    // --- Bulk Tagging Logic ---
    const handleSelectAll = (e) => {
        if (e.target.checked) {
            const allIds = new Set(sortedTransactions.map(t => t.transaction_id));
            setSelectedIds(allIds);
        } else {
            setSelectedIds(new Set());
        }
    };

    const handleSelectRow = (id) => {
        setSelectedIds(prev => {
            const newSet = new Set(prev);
            if (newSet.has(id)) newSet.delete(id);
            else newSet.add(id);
            return newSet;
        });
    };

    const handleBulkTagSubmit = async () => {
        if (!bulkTagInput.trim()) {
            alert("Please enter a tag to apply.");
            return;
        }
        if (selectedIds.size === 0) return;

        setIsBulkTagging(true);
        try {
            const response = await fetch('/api/transactions/bulk-tag', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    transaction_ids: Array.from(selectedIds),
                    tags: bulkTagInput.split(',').map(t => t.trim()).filter(Boolean)
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Bulk tagging failed');
            }
            
            alert(`Successfully tagged ${selectedIds.size} transactions.`);
            setBulkTagInput('');
            setSelectedIds(new Set());
            fetchData(activeFilters); // Refresh list to show new tags
        } catch (err) {
            alert(`Error: ${err.message}`);
        } finally {
            setIsBulkTagging(false);
        }
    };

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0, // Per request, use round dollars
        maximumFractionDigits: 0,
    }).format(value || 0);

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString();
    }

    const sumTotal = transactions.reduce((acc, tx) => acc + parseFloat(tx.amount || 0), 0);
    const hasActiveFilters = Object.values(activeFilters).some(v => v && v !== 'all');

    if (error) return <p>Error loading transactions: {error}</p>;

    return (
        <>
            <FilterPanel 
                config={filterConfig} 
                onFilterSubmit={handlePanelFilterSubmit} 
                initialValues={activeFilters}
            />

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
                <div className="chart-header">
                    <h2>Monthly Summary</h2>
                    <TimeFilter 
                        selectedPeriod={activeFilters.period || 'all'} 
                        onPeriodChange={handlePeriodChange} 
                    />
                </div>
                <div className="total-summary">
                    Filtered Total: <span>{formatCurrency(sumTotal)}</span>
                </div>
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
                
                {selectedIds.size > 0 && (
                    <div className="bulk-action-bar">
                        <div>
                            <strong>{selectedIds.size} transaction{selectedIds.size > 1 ? 's' : ''} selected.</strong>
                        </div>
                        <div>
                            <input 
                                type="text" 
                                placeholder="Enter tags (comma separated)" 
                                value={bulkTagInput}
                                onChange={(e) => setBulkTagInput(e.target.value)}
                            />
                            <button onClick={handleBulkTagSubmit} disabled={isBulkTagging}>
                                {isBulkTagging ? 'Applying...' : 'Apply Tags'}
                            </button>
                            <button className="btn-secondary" onClick={() => setSelectedIds(new Set())}>
                                Cancel
                            </button>
                        </div>
                    </div>
                )}

                {loading ? (
                    <p>Loading transactions...</p>
                ) : transactions.length > 0 ? (
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th className="checkbox-cell">
                                        <input 
                                            type="checkbox" 
                                            checked={sortedTransactions.length > 0 && selectedIds.size === sortedTransactions.length}
                                            onChange={handleSelectAll}
                                            title="Select all visible rows"
                                        />
                                    </th>
                                    <th className="sortable" onClick={() => requestSort('transaction_date')}>
                                        Date <span className="sort-indicator">{getSortIndicator('transaction_date')}</span>
                                    </th>
                                    <th className="sortable" onClick={() => requestSort('account_id')}>
                                        Account <span className="sort-indicator">{getSortIndicator('account_id')}</span>
                                    </th>
                                    <th className="sortable" onClick={() => requestSort('institution')}>
                                        Institution <span className="sort-indicator">{getSortIndicator('institution')}</span>
                                    </th>
                                    <th className="sortable" onClick={() => requestSort('description')}>
                                        Description <span className="sort-indicator">{getSortIndicator('description')}</span>
                                    </th>
                                    <th className="sortable" onClick={() => requestSort('cashflow_type')}>
                                        Cashflow Type <span className="sort-indicator">{getSortIndicator('cashflow_type')}</span>
                                    </th>
                                    <th className="sortable" onClick={() => requestSort('category')}>
                                        Category <span className="sort-indicator">{getSortIndicator('category')}</span>
                                    </th>
                                    <th className="sortable" onClick={() => requestSort('tags')}>
                                        Tags <span className="sort-indicator">{getSortIndicator('tags')}</span>
                                    </th>
                                    <th className="sortable" onClick={() => requestSort('amount')}>
                                        Amount <span className="sort-indicator">{getSortIndicator('amount')}</span>
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortedTransactions.map(t => (
                                    <tr key={t.transaction_id} onDoubleClick={() => setEditingTransaction(t)} style={{cursor: 'pointer'}} title="Double-click to edit">
                                        <td className="checkbox-cell" onClick={(e) => e.stopPropagation()}>
                                            <input 
                                                type="checkbox" 
                                                checked={selectedIds.has(t.transaction_id)}
                                                onChange={() => handleSelectRow(t.transaction_id)}
                                            />
                                        </td>
                                        <td>{formatDate(t.transaction_date)}</td>
                                        <td>{t.account_id}</td>
                                        <td>{t.institution}</td>
                                        <td>{t.description}</td>
                                        <td>{t.cashflow_type}</td>
                                        <td>{t.category}</td>
                                        <td>{t.tags}</td>
                                        <td style={{ color: t.amount > 0 ? 'var(--gold-accent)' : 'inherit', textAlign: 'right', fontFamily: 'monospace', fontSize: '1.1em' }}>
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

            {editingTransaction && (
                <TransactionEditorModal
                    transaction={editingTransaction}
                    onClose={() => setEditingTransaction(null)}
                    onSave={handleTransactionSave}
                />
            )}
        </>
    );
};

export default TransactionListView;
