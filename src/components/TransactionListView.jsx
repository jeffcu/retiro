import { useState, useEffect } from 'react';
import './TransactionListView.css';

const TransactionListView = () => {
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchTransactions = async () => {
            try {
                setLoading(true);
                const response = await fetch('/api/transactions');
                if (!response.ok) {
                    throw new Error(`HTTP Error: ${response.status}`);
                }
                const data = await response.json();
                setTransactions(data);
            } catch (e) {
                setError(e.message);
                console.error("Failed to fetch transactions:", e);
            } finally {
                setLoading(false);
            }
        };

        fetchTransactions();
    }, []);

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(value || 0);

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString();
    }

    if (loading) return <p>Loading transactions...</p>;
    if (error) return <p>Error loading transactions: {error}</p>;

    return (
        <div className="card">
            <h2>All Transactions</h2>
            {transactions.length > 0 ? (
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
                                    <td>{t.original_category || t.category}</td>
                                    <td style={{ color: t.amount > 0 ? 'var(--gold-accent)' : 'inherit' }}>
                                        {formatCurrency(t.amount)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <p>No transactions found. Please import a transaction CSV file via the 'Data & Settings' screen.</p>
            )}
        </div>
    );
};

export default TransactionListView;
