import { useState, useEffect } from 'react';
import './RulesEditor.css';

const RulesEditor = () => {
    const [rules, setRules] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [categories, setCategories] = useState([]);
    
    const initialFormState = {
        pattern: '',
        category: '',
        cashflow_type: 'Expense',
        tags: '',
        case_sensitive: false,
        account_filter_mode: 'include',
        account_filter_list: '',
    };
    const [formState, setFormState] = useState(initialFormState);

    const fetchRules = async () => {
        try {
            setIsLoading(true);
            const response = await fetch('/api/rules');
            if (!response.ok) throw new Error('Failed to fetch rules');
            const data = await response.json();
            setRules(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const fetchCategories = async () => {
        try {
            const response = await fetch('/api/filter-options');
            if (!response.ok) {
                throw new Error(`Failed to fetch categories: ${response.status}`);
            }
            const data = await response.json();
            console.log('RulesEditor: Fetched categories:', data.categories); // Diagnostic log
            setCategories(data.categories || []);
        } catch (error) {
            console.error("Failed to fetch categories for Rules Editor:", error);
        }
    };

    useEffect(() => {
        fetchRules();
        fetchCategories();
    }, []);

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormState(prevState => ({ 
            ...prevState, 
            [name]: type === 'checkbox' ? checked : value 
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const ruleData = {
            ...formState,
            tags: formState.tags.split(',').map(t => t.trim()).filter(Boolean),
            account_filter_list: formState.account_filter_list.split(',').map(a => a.trim()).filter(Boolean),
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
            fetchRules(); // Refresh rules list
            fetchCategories(); // Refresh categories list in case a new one was added
            setFormState(initialFormState);
        } catch (err) {
            alert(`Error creating rule: ${err.message}`);
        }
    };

    const handleDelete = async (ruleId) => {
        if (!confirm('Are you sure you want to delete this rule permanently?')) return;
        try {
            const response = await fetch(`/api/rules/${ruleId}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Failed to delete rule');
            fetchRules(); // Refresh the list
        } catch (err) {
            alert(`Error deleting rule: ${err.message}`);
        }
    };

    const handleRecategorize = async () => {
        if (!confirm('This will re-apply all rules to all transactions. This can take a moment. Continue?')) return;
        try {
            const response = await fetch('/api/transactions/recategorize', { method: 'POST' });
            if (!response.ok) throw new Error('Recategorization failed');
            const result = await response.json();
            alert(result.message);
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    }

    return (
        <div className="rules-editor-card">
            <h3>Categorization Rules Engine v2</h3>
            <form onSubmit={handleSubmit} className="rule-form">
                {/* Row 1: Core Pattern and Action */}
                <div className="form-group span-2">
                    <label>IF Description contains (Pattern/Regex)</label>
                    <input type="text" name="pattern" value={formState.pattern} onChange={handleInputChange} placeholder="e.g., safeway|amazon" required />
                </div>
                <div className="form-group">
                    <label>THEN set Category to</label>
                    <input 
                        type="text" 
                        name="category" 
                        value={formState.category} 
                        onChange={handleInputChange} 
                        placeholder="e.g., Groceries" 
                        list="main-rule-category-options"
                        required 
                    />
                    <datalist id="main-rule-category-options">
                        {categories.map(cat => (
                            <option key={cat} value={cat} />
                        ))}
                    </datalist>
                </div>
                <div className="form-group">
                    <label>Set Cashflow Type to</label>
                    <select name="cashflow_type" value={formState.cashflow_type} onChange={handleInputChange}>
                        <option value="Expense">Expense</option>
                        <option value="Income">Income</option>
                        <option value="Transfer">Transfer</option>
                        <option value="Capital Expenditure">Capital Expenditure</option>
                        <option value="Investment">Investment</option>
                    </select>
                </div>

                {/* Row 2: Advanced Filters */}
                <div className="form-group span-2">
                     <label>AND Account is</label>
                     <div className='account-filter-group'>
                        <select name="account_filter_mode" value={formState.account_filter_mode} onChange={handleInputChange}>
                            <option value="include">INCLUDED in list</option>
                            <option value="exclude">EXCLUDED from list</option>
                        </select>
                        <input type="text" name="account_filter_list" value={formState.account_filter_list} onChange={handleInputChange} placeholder="checking, savings (optional, comma-separated)" />
                     </div>
                </div>
                <div className="form-group">
                    <label>Add Tags (optional)</label>
                    <input type="text" name="tags" value={formState.tags} onChange={handleInputChange} placeholder="vacation, travel2024" />
                </div>
                <div className="form-group checkbox-group">
                    <input type="checkbox" id="case_sensitive" name="case_sensitive" checked={formState.case_sensitive} onChange={handleInputChange} />
                    <label htmlFor="case_sensitive">Case-Sensitive Match</label>
                </div>

                <button type="submit" className='add-rule-btn'>Add Rule</button>
            </form>

            <h4>Existing Rules</h4>
            <div className="rules-table">
                <table>
                    <thead>
                        <tr>
                            <th>Pattern</th>
                            <th>Conditions</th>
                            <th>Category</th>
                            <th>Type</th>
                            <th>Tags</th>
                            <th className="actions-cell"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading ? (
                            <tr><td colSpan="6">Loading rules...</td></tr>
                        ) : rules.map(rule => (
                            <tr key={rule.rule_id}>
                                <td className='pattern-cell'>{rule.pattern}</td>
                                <td className='conditions-cell'>
                                    {rule.case_sensitive && <span className='condition-tag'>Case-Sensitive</span>}
                                    {rule.account_filter_list && rule.account_filter_list.length > 0 && 
                                        <span className='condition-tag'>
                                            Account {rule.account_filter_mode === 'include' ? 'IN' : 'NOT IN'} [{rule.account_filter_list.join(', ')}]
                                        </span>
                                    }
                                </td>
                                <td>{rule.category}</td>
                                <td>{rule.cashflow_type}</td>
                                <td>{rule.tags.join(', ')}</td>
                                <td className="actions-cell">
                                    <button className="delete-btn" onClick={() => handleDelete(rule.rule_id)} title="Delete Rule">🗑️</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="form-actions">
                <button onClick={handleRecategorize} className="secondary">Re-categorize All Transactions</button>
            </div>
        </div>
    );
};

export default RulesEditor;
