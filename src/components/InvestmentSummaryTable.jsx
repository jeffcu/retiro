import { useState, useEffect } from 'react';
import './InvestmentSummaryTable.css';

const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
}).format(value || 0);

const InvestmentSummaryTable = ({ period }) => {
    const [summary, setSummary] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                setIsLoading(true);
                const response = await fetch(`/api/analysis/investment-cashflow-summary?period=${period}`);
                if (!response.ok) {
                    throw new Error('Failed to fetch investment cashflow summary');
                }
                const data = await response.json();
                setSummary(data);
            } catch (error) {
                console.error(error);
                setSummary(null);
            } finally {
                setIsLoading(false);
            }
        };
        fetchSummary();
    }, [period]);

    if (isLoading) {
        return (
            <div className="card investment-summary-card">
                <h2>Portfolio Cashflow Summary</h2>
                <p>Loading summary...</p>
            </div>
        );
    }
    
    if (!summary) {
        return null; // Don't render if there's no data or an error
    }

    return (
        <div className="card investment-summary-card">
            <h2>Portfolio Cashflow Summary</h2>
            <table className="summary-table">
                <tbody>
                    <tr>
                        <td>Investment Income (Yield)</td>
                        <td className="positive">{formatCurrency(summary.investment_income)}</td>
                    </tr>
                    <tr>
                        <td>Advisory & Management Fees</td>
                        <td className="negative">({formatCurrency(summary.advisory_fees)})</td>
                    </tr>
                    <tr>
                        <td>Estimated Taxes on Yield</td>
                        <td className="negative">({formatCurrency(summary.estimated_taxes)})</td>
                    </tr>
                </tbody>
                <tfoot>
                    <tr>
                        <td>Spendable Cash from Portfolio</td>
                        <td>{formatCurrency(summary.spendable_cash)}</td>
                    </tr>
                </tfoot>
            </table>
            <p className="summary-notes"><em>{summary.notes}</em></p>
        </div>
    );
};

export default InvestmentSummaryTable;
