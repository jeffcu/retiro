import { useState, useEffect } from 'react';
import './TransactionEditorModal.css';

const TransactionEditorModal = ({ transaction, onClose, onSave }) => {
    const [formData, setFormData] = useState({
        description: '',
        category: '',
        cashflow_type: '',
        tags: '',
    });
    const [cashflowTypes, setCashflowTypes] = useState([]);

    useEffect(() => {
        if (transaction) {
            setFormData({
                description: transaction.description || '',
                category: transaction.category || '',
                cashflow_type: transaction.cashflow_type || 'Expense',
                tags: Array.isArray(transaction.tags) ? transaction.tags.join(', ') : (transaction.tags || ''),
            });
        }
    }, [transaction]);

    useEffect(() => {
        // Fetch cashflow types for the dropdown
        const fetchOptions = async () => {
            try {
                const response = await fetch('/api/filter-options');
                if (!response.ok) throw new Error('Failed to fetch options');
                const data = await response.json();
                setCashflowTypes(data.cashflowTypes || []);
            } catch (error) {
                console.error("Couldn't fetch cashflow types:", error);
            }
        };
        fetchOptions();
    }, []);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSave = async (e) => {
        e.preventDefault();
        const updatePayload = {
            ...formData,
            tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
        };

        try {
            const response = await fetch(`/api/transactions/${transaction.transaction_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatePayload),
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to update transaction');
            }
            onSave(); // This will trigger a refresh and close the modal
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    if (!transaction) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <h2>Edit Transaction</h2>
                <form onSubmit={handleSave} className="modal-form">
                    <div className="form-group full-width">
                        <label>Description</label>
                        <input type="text" name="description" value={formData.description} onChange={handleChange} required />
                    </div>
                    <div className="form-grid">
                        <div className="form-group">
                            <label>Category</label>
                            <input type="text" name="category" value={formData.category} onChange={handleChange} placeholder="e.g., Groceries" />
                        </div>
                        <div className="form-group">
                            <label>Cashflow Type</label>
                            <select name="cashflow_type" value={formData.cashflow_type} onChange={handleChange}>
                                {cashflowTypes.map(type => (
                                    <option key={type} value={type}>{type}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                    <div className="form-group full-width">
                        <label>Tags (comma-separated)</label>
                        <input type="text" name="tags" value={formData.tags} onChange={handleChange} placeholder="e.g., vacation, project-x" />
                    </div>
                    <div className="modal-actions">
                        <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
                        <button type="submit" className="btn-primary">Save Changes</button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default TransactionEditorModal;
