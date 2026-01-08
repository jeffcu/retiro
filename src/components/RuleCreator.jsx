import { useState } from 'react';
import './RuleCreator.css';

const RuleCreator = ({ filters, onSave, onCancel }) => {
    const [actionState, setActionState] = useState({
        set_category: '',
        set_cashflow_type: 'Expense',
        add_tags: '',
    });

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setActionState(prevState => ({ ...prevState, [name]: value }));
    };
    
    const handleSubmit = async (e) => {
        e.preventDefault();
        const ruleData = {
            // Actions from form
            category: actionState.set_category,
            cashflow_type: actionState.set_cashflow_type,
            tags: actionState.add_tags.split(',').map(t => t.trim()).filter(Boolean),
            
            // Conditions from filters prop
            pattern: filters.description || null,
            account_filter_list: filters.account_id ? [filters.account_id] : [],
            condition_category: filters.category || null,
            condition_institution: filters.institution || null,
            condition_cashflow_type: filters.cashflow_type || null,
            condition_tags: filters.tags || null,
        };
        
        try {
            const response = await fetch('/api/rules', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(ruleData),
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to create rule');
            }
            onSave();
        } catch (err) {
            alert(`Error creating rule: ${err.message}`);
        }
    };

    const conditionItems = Object.entries(filters)
        .filter(([, value]) => value)
        .map(([key, value]) => <li key={key}><strong>{key.replace(/_/g, ' ')}:</strong> <em>{value}</em></li>);

    return (
        <div className="card rule-creator-card">
            <h3>Create Rule from Filter</h3>
            
            <h4>IF a transaction matches ALL of these conditions:</h4>
            <ul className="condition-list">
                {conditionItems.length > 0 ? conditionItems : <li>No conditions defined by filter.</li>}
            </ul>

            <form onSubmit={handleSubmit}>
                <h4>THEN apply this action:</h4>
                 <div className="form-grid">
                    <div className="form-group">
                        <label>Set Category to</label>
                        <input type="text" name="set_category" value={actionState.set_category} onChange={handleInputChange} placeholder="e.g., Groceries" required />
                    </div>
                    <div className="form-group">
                        <label>Set Cashflow Type to</label>
                        <select name="set_cashflow_type" value={actionState.set_cashflow_type} onChange={handleInputChange}>
                            <option value="Expense">Expense</option>
                            <option value="Income">Income</option>
                            <option value="Transfer">Transfer</option>
                            <option value="Capital Expenditure">Capital Expenditure</option>
                            <option value="Investment">Investment</option>
                        </select>
                    </div>
                     <div className="form-group">
                        <label>Add Tags (comma-separated)</label>
                        <input type="text" name="add_tags" value={actionState.add_tags} onChange={handleInputChange} placeholder="e.g., vacation" />
                    </div>
                </div>
                
                <div className="form-actions">
                    <button type="submit" className="primary">Save Rule & Recategorize</button>
                    <button type="button" onClick={onCancel}>Cancel</button>
                </div>
            </form>
        </div>
    );
};

export default RuleCreator;
