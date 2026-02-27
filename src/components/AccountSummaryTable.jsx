import { useState, useEffect } from 'react';
import './AccountSummaryTable.css';
import { useMode } from '../context/ModeContext';

const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
}).format(value || 0);

const AccountSummaryTable = () => {
    const { mode } = useMode();
    const [data, setData] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            setIsLoading(true);
            try {
                const response = await fetch(`/api/accounts/performance?mode=${mode}`);
                if (!response.ok) throw new Error('Failed to fetch account summary');
                const result = await response.json();
                setData(result);
            } catch (error) {
                console.error("Error fetching account summary:", error);
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, [mode]);

    const getStatusClass = (status) => {
        const s = (status || '').toLowerCase();
        if (s.includes('deferred') || s.includes('ira') || s.includes('401')) return 'status-deferred';
        if (s.includes('roth')) return 'status-roth';
        if (s.includes('exempt')) return 'status-exempt';
        return 'status-taxable';
    };

    // Helper to group by Institution/Group ID for display if needed
    // Currently API returns flat list sorted by group. 
    // We'll just render flat for now but with visual distinction for sub-accounts.
    
    return (
        <div className="card account-summary-card">
            <h2>Investment Accounts Summary</h2>
            {isLoading ? <p>Loading account data...</p> : (
                <table className="account-summary-table">
                    <thead>
                        <tr>
                            <th>Account Name</th>
                            <th>Tax Setting</th>
                            <th>Total Value</th>
                            <th>Cost Basis</th>
                            <th>Total Gain/Loss</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.length === 0 ? (
                            <tr><td colSpan="5">No investment accounts found.</td></tr>
                        ) : data.map(acc => (
                            <tr key={acc.lookup_key}>
                                <td>
                                    {/* Indent if it's a sub-account (has an account number) */}
                                    {acc.account_number ? (
                                        <span style={{paddingLeft: '1.5rem', color: '#ccc', fontSize: '0.9em'}}>
                                            ↳ {acc.account_number}
                                        </span>
                                    ) : (
                                        <span style={{fontWeight: '500'}}>{acc.group_id}</span>
                                    )}
                                </td>
                                <td>
                                    <span className={`tax-status-badge ${getStatusClass(acc.tax_status)}`}>
                                        {acc.tax_status}
                                    </span>
                                </td>
                                <td>{formatCurrency(acc.total_market_value)}</td>
                                <td>{formatCurrency(acc.total_cost_basis)}</td>
                                <td className={acc.total_gain >= 0 ? 'gain-positive' : 'gain-negative'}>
                                    {formatCurrency(acc.total_gain)} 
                                    <span style={{fontSize:'0.8em', marginLeft:'5px', opacity:0.8}}>
                                        ({acc.total_gain_percent.toFixed(1)}%)
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
};

export default AccountSummaryTable;
