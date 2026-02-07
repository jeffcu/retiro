import { useState, useEffect } from 'react';
import './FutureIncomeStreamEditor.css';

const FutureIncomeStreamEditor = () => {
    const [streams, setStreams] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const initialFormState = {
        stream_type: 'Social Security',
        description: '',
        start_date: '',
        amount: '',
        frequency: 'monthly',
        annual_increase_rate: 0.0,
    };
    const [formData, setFormData] = useState(initialFormState);

    const fetchStreams = async () => {
        setIsLoading(true);
        try {
            const response = await fetch('/api/future-streams');
            if (!response.ok) throw new Error('Failed to fetch future income streams');
            const data = await response.json();
            setStreams(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchStreams();
    }, []);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        const payload = {
            ...formData,
            amount: parseFloat(formData.amount),
            annual_increase_rate: parseFloat(formData.annual_increase_rate) / 100, // Convert percentage to decimal
        };

        try {
            const response = await fetch('/api/future-streams', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to create stream');
            }
            setFormData(initialFormState); // Reset form
            fetchStreams(); // Refresh list
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    const handleDelete = async (streamId) => {
        if (!confirm('Are you sure you want to delete this income stream?')) return;

        try {
            const response = await fetch(`/api/future-streams/${streamId}`, {
                method: 'DELETE',
            });
            if (!response.ok) throw new Error('Failed to delete stream');
            fetchStreams(); // Refresh list
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(value || 0);

    return (
        <div className="future-stream-editor-container">
            <h3>Future Income Streams (for Forecasting)</h3>
            <p>Define recurring income streams like pensions or Social Security that will begin in the future.</p>
            
            <form onSubmit={handleSubmit} className="stream-form">
                <div className="form-grid">
                    <div className="form-group">
                        <label>Type</label>
                        <select name="stream_type" value={formData.stream_type} onChange={handleInputChange}>
                            <option value="Social Security">Social Security</option>
                            <option value="Pension">Pension</option>
                            <option value="RMD">RMD</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                    <div className="form-group">
                        <label>Description</label>
                        <input type="text" name="description" value={formData.description} onChange={handleInputChange} placeholder="e.g., Captain Primary SS" required />
                    </div>
                    <div className="form-group">
                        <label>Start Date</label>
                        <input type="date" name="start_date" value={formData.start_date} onChange={handleInputChange} required />
                    </div>
                     <div className="form-group">
                        <label>Amount (per period)</label>
                        <input type="number" name="amount" value={formData.amount} onChange={handleInputChange} placeholder="3250.75" step="0.01" required />
                    </div>
                    <div className="form-group">
                        <label>Frequency</label>
                        <select name="frequency" value={formData.frequency} onChange={handleInputChange}>
                            <option value="monthly">Monthly</option>
                            <option value="annually">Annually</option>
                        </select>
                    </div>
                    <div className="form-group">
                        <label>Annual Increase Rate (%)</label>
                        <input type="number" name="annual_increase_rate" value={formData.annual_increase_rate} onChange={handleInputChange} placeholder="2.5" step="0.1" />
                    </div>
                </div>
                 <div className="form-actions">
                    <button type="submit" className="primary">Add Income Stream</button>
                </div>
            </form>

            <h4>Existing Streams</h4>
            <div className="streams-table-container">
                {isLoading ? <p>Loading streams...</p> : error ? <p className="error-message">{error}</p> : (
                    <table className="streams-table">
                        <thead>
                            <tr>
                                <th>Description</th>
                                <th>Type</th>
                                <th>Start Date</th>
                                <th>Amount</th>
                                <th>Frequency</th>
                                <th>COLA</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {streams.length === 0 ? (
                                <tr><td colSpan="7">No future income streams defined.</td></tr>
                            ) : streams.map(stream => (
                                <tr key={stream.stream_id}>
                                    <td>{stream.description}</td>
                                    <td>{stream.stream_type}</td>
                                    <td>{stream.start_date}</td>
                                    <td>{formatCurrency(stream.amount)}</td>
                                    <td>{stream.frequency}</td>
                                    <td>{`${(stream.annual_increase_rate * 100).toFixed(1)}%`}</td>
                                    <td className="actions-cell">
                                        <button className="delete-btn" onClick={() => handleDelete(stream.stream_id)} title="Delete Stream">🗑️</button>
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

export default FutureIncomeStreamEditor;
