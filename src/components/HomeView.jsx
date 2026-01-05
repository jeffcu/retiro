import { useState, useEffect } from 'react';
import SankeyChart from '../SankeyChart';
import MockSankey from './MockSankey';
import './HomeView.css';

const NetWorthHero = () => {
    const [netWorth, setNetWorth] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                setLoading(true);
                const response = await fetch('/api/portfolio/summary');
                if (!response.ok) throw new Error('Failed to fetch summary');
                const data = await response.json();
                setNetWorth(data.total_market_value);
            } catch (error) {
                console.error('Error fetching net worth:', error);
                setNetWorth(0); // Default to 0 on error
            } finally {
                setLoading(false);
            }
        };
        fetchSummary();
    }, []);

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0,
    }).format(value);

    return (
        <div className="net-worth-hero">
            <h2>Latest Net Worth</h2>
            <p className="value">
                {loading ? 'Calculating...' : formatCurrency(netWorth)}
            </p>
            <p className="timestamp">As of latest holdings import</p>
        </div>
    );
};

const HomeView = () => {
    const [incomeSankeyData, setIncomeSankeyData] = useState(null);

    useEffect(() => {
        const fetchSankeyData = async () => {
            try {
                const response = await fetch('/api/sankey/income');
                if (!response.ok) throw new Error('Failed to fetch income sankey');
                const data = await response.json();
                setIncomeSankeyData(data);
            } catch (error) {
                console.error(error);
            }
        };
        fetchSankeyData();
    }, []);

    const isChartVisible = incomeSankeyData && incomeSankeyData.links.length > 0;

    return (
        <>
            <NetWorthHero />
            <div className="grid-container">
                <div className="card">
                    <h2>Income → Uses of Money</h2>
                    {isChartVisible ? (
                        <SankeyChart data={incomeSankeyData} />
                    ) : (
                        <p>No transaction data found for this chart.</p>
                    )}
                </div>
                <div className="card">
                    <h2>Portfolio Return Waterfall</h2>
                    <MockSankey type="returns" />
                </div>
            </div>
        </>
    );
};

export default HomeView;
