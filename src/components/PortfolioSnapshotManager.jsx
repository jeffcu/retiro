import { useState, useEffect } from 'react';
import './PortfolioSnapshotManager.css';

const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD',
}).format(value || 0);

const formatDate = (isoString) => new Date(isoString + 'T00:00:00').toLocaleDateString();

const PortfolioSnapshotManager = () => {
    const [snapshots, setSnapshots] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const initialFormState = { snapshot_date: '', market_value: '' };
    const [formData, setFormData] = useState(initialFormState);

    const fetchSnapshots = async () => {
        setIsLoading(true);
        try {
            const response = await fetch('/api/portfolio/snapshots');
            if (!response.ok) throw new Error('Failed to fetch snapshots');
            const data = await response.json();
            setSnapshots(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchSnapshots();
    }, []);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const payload = {
            ...formData,
            market_value: parseFloat(formData.market_value),
        };
        try {
            const response = await fetch('/api/portfolio/snapshots', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to create snapshot');
            }
            setFormData(initialFormState);
            fetchSnapshots();
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    const handleDelete = async (snapshotId) => {
        if (!confirm('Are you sure you want to delete this snapshot?')) return;
        try {
            const response = await fetch(`/api/portfolio/snapshots/${snapshotId}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Failed to delete snapshot');
            fetchSnapshots();
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    return (
        <div className="snapshot-manager-container">
            <h3>Portfolio Value Snapshots</h3>
            <p>Enter historical portfolio market values to enable accurate performance reporting.</p>
            
            <form onSubmit={handleSubmit} className="snapshot-form">
                <div className="form-grid">
                    <div className="form-group">
                        <label>Snapshot Date</label>
                        <input type="date" name="snapshot_date" value={formData.snapshot_date} onChange={handleInputChange} required />
                    </div>
                    <div className="form-group">
                        <label>Total Market Value</label>
                        <input type="number" name="market_value" value={formData.market_value} onChange={handleInputChange} placeholder="1234567.89" step="0.01" required />
                    </div>
                </div>
                <div className="form-actions">
                    <button type="submit" className="primary">Add/Update Snapshot</button>
                </div>
            </form>

            <h4>Existing Snapshots</h4>
            <div className="snapshots-table-container">
                {isLoading ? <p>Loading snapshots...</p> : error ? <p className="error-message">{error}</p> : (
                    <table className="snapshots-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Market Value</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {snapshots.length === 0 ? (
                                <tr><td colSpan="3">No snapshots entered yet.</td></tr>
                            ) : snapshots.map(s => (
                                <tr key={s.snapshot_id}>
                                    <td>{formatDate(s.snapshot_date)}</td>
                                    <td>{formatCurrency(s.market_value)}</td>
                                    <td className="actions-cell">
                                        <button className="delete-btn" onClick={() => handleDelete(s.snapshot_id)} title="Delete">🗑️</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};

export default PortfolioSnapshotManager;
