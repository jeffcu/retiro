import { useState, useEffect } from 'react';

const RulesManager = ({ onRuleAdded }) => {
    const [rules, setRules] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Form state
    const [pattern, setPattern] = useState('');
    const [category, setCategory] = useState('');
    const [cashflowType, setCashflowType] = useState('Expense');

    const fetchRules = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/rules');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setRules(data);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRules();
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!pattern || !category) {
            alert('Please fill in both Pattern and Category.');
            return;
        }

        const newRule = { 
            pattern,
            category,
            cashflow_type: cashflowType,
        };

        try {
            const response = await fetch('/api/rules', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newRule),
            });

            if (!response.ok) {
                throw new Error(`Failed to create rule: ${response.statusText}`);
            }

            // Reset form
            setPattern('');
            setCategory('');
            setCashflowType('Expense');

            // Refetch rules to show the new one in the list
            await fetchRules(); 

            // Notify parent component that the rules have changed
            if (onRuleAdded) {
                onRuleAdded();
            }

        } catch (error) {
            console.error("Error creating rule:", error);
            alert(`Error: ${error.message}`);
        }
    };

    return (
        <div className="rules-manager-container">
            <div className="rules-list">
                <h3>Existing Rules</h3>
                {loading && <p>Loading rules...</p>}
                {error && <p>Error loading rules: {error}</p>}
                {rules.length > 0 ? (
                    <ul>
                        {rules.map(rule => (
                            <li key={rule.rule_id}>
                                "{rule.pattern}" → <span>{rule.category} ({rule.cashflow_type})</span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    !loading && <p>No rules defined yet.</p>
                )}
            </div>
            <div className="rule-form">
                <h3>Create New Rule</h3>
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="pattern">If description contains:</label>
                        <input 
                            id="pattern" 
                            type="text" 
                            value={pattern} 
                            onChange={e => setPattern(e.target.value)} 
                            placeholder="e.g., Safeway"
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="category">Categorize as:</label>
                        <input 
                            id="category" 
                            type="text" 
                            value={category} 
                            onChange={e => setCategory(e.target.value)} 
                            placeholder="e.g., Groceries"
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="cashflowType">Transaction Type:</label>
                        <select 
                            id="cashflowType" 
                            value={cashflowType} 
                            onChange={e => setCashflowType(e.target.value)}
                        >
                            <option value="Expense">Expense</option>
                            <option value="Income">Income</option>
                            <option value="Transfer">Transfer</option>
                            <option value="Capital Expenditure">Capital Expenditure</option>
                        </select>
                    </div>
                    <button type="submit">Create Rule</button>
                    <p className='note'>
                        <strong>Note:</strong> After adding a rule, you must re-import your CSV file to see its effects on existing transactions.
                    </p>
                </form>
            </div>
        </div>
    );
};

export default RulesManager;
