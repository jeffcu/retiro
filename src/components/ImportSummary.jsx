import { useEffect, useState } from 'react';
import './ImportSummary.css';

const ImportSummary = ({ refreshKey }) => {
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchRuns = async () => {
            try {
                setLoading(true);
                const response = await fetch('/api/import/runs');
                if (!response.ok) {
                    throw new Error(`HTTP Error: ${response.status}`);
                }
                const data = await response.json();
                setRuns(data);
            } catch (e) {
                setError(e.message);
                console.error("Failed to fetch import runs:", e);
            } finally {
                setLoading(false);
            }
        };

        fetchRuns();
    }, [refreshKey]); // Re-fetch when refreshKey changes

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(value || 0);

    const formatDate = (isoString) => {
        if (!isoString) return 'N/A';
        return new Date(isoString).toLocaleString();
    }

    if (loading) return <p>Loading import history...</p>;
    if (error) return <p>Error loading import history: {error}</p>;

    const transactionRuns = runs.filter(r => r.import_type === 'transactions');
    const holdingRuns = runs.filter(r => r.import_type === 'holdings');

    return (
        <div className="import-summary-container card">
            <h2>Import History & Verification</h2>
            {runs.length === 0 ? (
                <p>No import history found.</p>
            ) : (
                <div className="summary-tables-grid">
                    <div className="summary-table-wrapper">
                        <h3>Transactions</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>File Name</th>
                                    <th>Imported At</th>
                                    <th>Rows</th>
                                    <th>Total Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                                {transactionRuns.map(run => (
                                    <tr key={run.import_run_id}>
                                        <td>{run.file_name}</td>
                                        <td>{formatDate(run.import_timestamp)}</td>
                                        <td>{run.record_count}</td>
                                        <td>{formatCurrency(run.total_amount)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <div className="summary-table-wrapper">
                        <h3>Holdings</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>File Name</th>
                                    <th>Imported At</th>
                                    <th>Assets</th>
                                    <th>Total Market Value</th>
                                    <th>Total Cost Basis</th>
                                </tr>
                            </thead>
                            <tbody>
                                {holdingRuns.map(run => (
                                    <tr key={run.import_run_id}>
                                        <td>{run.file_name}</td>
                                        <td>{formatDate(run.import_timestamp)}</td>
                                        <td>{run.record_count}</td>
                                        <td>{formatCurrency(run.total_market_value)}</td>
                                        <td>{formatCurrency(run.total_cost_basis)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ImportSummary;
