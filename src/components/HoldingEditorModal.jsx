import { useState, useEffect } from 'react';
import './HoldingEditorModal.css'; // Re-using the same modal styles for consistency

const HoldingEditorModal = ({ holding, onClose, onSave }) => {
    const [tags, setTags] = useState('');

    useEffect(() => {
        if (holding) {
            setTags(Array.isArray(holding.tags) ? holding.tags.join(', ') : '');
        }
    }, [holding]);

    const handleSave = async (e) => {
        e.preventDefault();
        const updatePayload = {
            tags: tags.split(',').map(t => t.trim()).filter(Boolean),
        };

        try {
            const response = await fetch(`/api/holdings/${holding.holding_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatePayload),
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to update holding');
            }
            onSave(); // This will trigger a refresh and close the modal
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    if (!holding) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <h2>Edit Tags for {holding.symbol}</h2>
                <p><strong>Account:</strong> {holding.account_id}</p>
                <form onSubmit={handleSave} className="modal-form">
                    <div className="form-group full-width">
                        <label>Tags (comma-separated)</label>
                        <input 
                            type="text" 
                            name="tags" 
                            value={tags} 
                            onChange={(e) => setTags(e.target.value)} 
                            placeholder="e.g., core, speculative"
                            autoFocus
                        />
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

export default HoldingEditorModal;
