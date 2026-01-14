import { useState, useEffect } from 'react';
import './HoldingEditorModal.css'; // Re-using the same modal styles for consistency

const HoldingEditorModal = ({ holding, onClose, onSave }) => {
    const [tags, setTags] = useState('');
    const [assetType, setAssetType] = useState('');
    const [assetTypeOptions, setAssetTypeOptions] = useState([]);

    useEffect(() => {
        const fetchOptions = async () => {
            try {
                const response = await fetch('/api/filter-options');
                if (!response.ok) throw new Error('Failed to fetch options');
                const data = await response.json();
                setAssetTypeOptions(data.assetTypes || []);
            } catch (error) {
                console.error("Failed to fetch asset type options", error);
            }
        };
        fetchOptions();
    }, []);

    useEffect(() => {
        if (holding) {
            setTags(Array.isArray(holding.tags) ? holding.tags.join(', ') : '');
            setAssetType(holding.asset_type || '');
        }
    }, [holding]);

    const handleSave = async (e) => {
        e.preventDefault();
        const updatePayload = {
            tags: tags.split(',').map(t => t.trim()).filter(Boolean),
            asset_type: assetType.trim() || null,
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
                <h2>Edit Holding: {holding.symbol}</h2>
                <p><strong>Account:</strong> {holding.account_id}</p>
                <form onSubmit={handleSave} className="modal-form">
                    <div className="form-group full-width">
                        <label>Asset Type</label>
                        <input 
                            type="text" 
                            name="asset_type" 
                            value={assetType} 
                            onChange={(e) => setAssetType(e.target.value)} 
                            placeholder="e.g., Stock, ETF, Mutual Fund"
                            list="asset-type-options"
                        />
                         <datalist id="asset-type-options">
                            {assetTypeOptions.map(opt => (
                                <option key={opt} value={opt} />
                            ))}
                        </datalist>
                    </div>
                    <div className="form-group full-width">
                        <label>Tags (comma-separated)</label>
                        <input 
                            type="text" 
                            name="tags" 
                            value={tags} 
                            onChange={(e) => setTags(e.target.value)} 
                            placeholder="e.g., core, speculative"
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
