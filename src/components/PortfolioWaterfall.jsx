import { useState, useEffect } from 'react';
import TimeFilter from './TimeFilter';
import './PortfolioWaterfall.css';

const formatCurrency = (value, sign = 'none') => {
    if (value === null || typeof value === 'undefined') return 'N/A';
    
    const formatted = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.abs(value));

    if (sign === 'always' && value > 0) return `+${formatted}`;
    if (value < 0) return `(${formatted})`;
    return formatted;
};

const PortfolioWaterfall = () => {
    const [data, setData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [period, setPeriod] = useState('2024'); // Default to current year for relevance

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                setError(null);
                const response = await fetch(`/api/analysis/portfolio-waterfall?period=${period}`);
                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || 'Failed to fetch waterfall data');
                }
                setData(await response.json());
            } catch (err) {
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, [period]);

    return (
        <div className="card waterfall-card">
            <h2>
                Portfolio Performance Waterfall
                <TimeFilter selectedPeriod={period} onPeriodChange={setPeriod} />
            </h2>
            {isLoading && <p>Loading analysis...</p>}
            {error && <p className="error">Error: {error}</p>}
            {data && !isLoading && (
                <>
                    <table className="waterfall-table">
                        <tbody>
                            <tr>
                                <td>Start of Period Value</td>
                                <td>{formatCurrency(data.start_of_period_value)}</td>
                            </tr>
                            <tr>
                                <td>(+) External Contributions</td>
                                <td className="positive">{formatCurrency(data.external_contributions)}</td>
                            </tr>
                            <tr>
                                <td>(+) Portfolio Yield</td>
                                <td className="positive">{formatCurrency(data.portfolio_yield)}</td>
                            </tr>
                            <tr>
                                <td>(-) Withdrawals for Spending</td>
                                <td className="negative">({formatCurrency(data.withdrawals_for_spending)})</td>
                            </tr>
                            <tr>
                                <td>(-) Fees & Estimated Taxes</td>
                                <td className="negative">({formatCurrency(data.fees_and_estimated_taxes)})</td>
                            </tr>
                            <tr className="total-row">
                                <td>Net Cash Flow</td>
                                <td className={data.net_cash_flow >= 0 ? 'positive' : 'negative'}>
                                    {formatCurrency(data.net_cash_flow, 'always')}
                                </td>
                            </tr>
                            <tr>
                                <td>(+) Market Growth / (Loss)</td>
                                <td className={data.market_growth_or_loss >= 0 ? 'positive' : 'negative'}>
                                    {formatCurrency(data.market_growth_or_loss, 'always')}
                                </td>
                            </tr>
                             <tr className="total-row">
                                <td>End of Period Value</td>
                                <td>{formatCurrency(data.end_of_period_value)}</td>
                            </tr>
                        </tbody>
                    </table>
                    <p className="waterfall-notes"><em>{data.notes}</em></p>
                </>
            )}
        </div>
    );
};

export default PortfolioWaterfall;
