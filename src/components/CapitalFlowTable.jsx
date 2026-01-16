import { useState, useEffect } from 'react';
import './CapitalFlowTable.css';

const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
}).format(value || 0);

const FlowSection = ({ title, data, total, isSubSection = false }) => (
    <div className="flow-table-container">
        <h3>{title}</h3>
        <table className="flow-table">
            <tbody>
                {Object.entries(data).map(([key, value]) => (
                    <tr key={key}>
                        <td>{key}</td>
                        <td>{formatCurrency(value)}</td>
                    </tr>
                ))}
            </tbody>
            {!isSubSection && (
                <tfoot>
                    <tr>
                        <td>Total</td>
                        <td>{formatCurrency(total)}</td>
                    </tr>
                </tfoot>
            )}
        </table>
    </div>
);

const CapitalFlowTable = ({ period }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [data, setData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                const response = await fetch(`/api/analysis/capital-flow-table?period=${period}`);
                if (!response.ok) throw new Error('Failed to fetch capital flow table data');
                setData(await response.json());
            } catch (error) {
                console.error(error);
                setData(null);
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, [period]);

    if (isLoading) {
        return <div className="card"><p>Loading flow details...</p></div>;
    }

    if (!data || data.total_inflows <= 0) {
        return null; // Don't render if there's no data
    }

    const inflowsData = {
        ...data.inflows_by_category,
        'Portfolio Yield': data.portfolio_yield
    };

    const expensesData = {
        ...data.consumption_breakdown.top_categories,
        'Other Expenses': data.consumption_breakdown.other_total
    };
    
    return (
        <div className="collapsible-card">
            <header className="collapsible-header" onClick={() => setIsOpen(!isOpen)}>
                <h2>Tabular Capital Flow</h2>
                <span className={`toggle-icon ${isOpen ? 'open' : ''}`}>▶</span>
            </header>
            {isOpen && (
                <div className="collapsible-content">
                    <FlowSection title="Inflows" data={inflowsData} total={data.total_inflows} />
                    <FlowSection title="Consumption" data={expensesData} total={data.total_consumption} />
                </div>
            )}
        </div>
    );
};

export default CapitalFlowTable;
