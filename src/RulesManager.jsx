import { useState, useEffect } from 'react';

const RulesManager = ({ onRuleAdded }) => {
    const [rules, setRules] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

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

        setIsSubmitting(true);

        const newRule = { 
            pattern,
            category,
            cashflow_type: cashflowType,
        };

        try {
            // Step 1: Create the new rule
            const createRuleResponse = await fetch('/api/rules', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newRule),
            });

            if (!createRuleResponse.ok) {
                throw new Error(`Failed to create rule: ${createRuleResponse.statusText}`);
            }

            // Step 2: Trigger the backend to re-categorize all transactions
            const recategorizeResponse = await fetch('/api/transactions/recategorize', {
                method: 'POST',
            });

            if (!recategorizeResponse.ok) {
                throw new Error(`Failed to re-categorize transactions: ${recategorizeResponse.statusText}`);
            }

            // Reset form
            setPattern('');
            setCategory('');
            setCashflowType('Expense');

            // Notify parent component to refresh all data, which implicitly fetches the new rule list as well.
            if (onRuleAdded) {
                onRuleAdded();
            }

        } catch (error) {
            console.error("Error during rule creation and re-categorization:", error);
            alert(`Error: ${error.message}`);
        } finally {
            setIsSubmitting(false);
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
                            disabled={isSubmitting}
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
                            disabled={isSubmitting}
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="cashflowType">Transaction Type:</label>
                        <select 
                            id="cashflowType" 
                            value={cashflowType} 
                            onChange={e => setCashflowType(e.target.value)}
                            disabled={isSubmitting}
                        >
                            <option value="Expense">Expense</option>
                            <option value="Income">Income</option>
                            <option value="Transfer">Transfer</option>
                            <option value="Capital Expenditure">Capital Expenditure</option>
                        </select>
                    </div>
                    <button type="submit" disabled={isSubmitting}>
                        {isSubmitting ? 'Processing...' : 'Create Rule & Apply'}
                    </button>
                    <p className='note'>
                        <strong>Note:</strong> Creating a rule now automatically re-categorizes all existing transactions.
                    </p>
                </form>
            </div>
        </div>
    );
};

export default RulesManager;
