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
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value || 0);

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

const TimeFilter = ({ selectedPeriod, onPeriodChange }) => {
    const periods = [
        { id: 'all', label: 'All Time' },
        { id: '2025', label: '2025' },
        { id: '2024', label: '2024' },
        { id: '6m', label: 'Last 6 Months' },
        { id: '3m', label: 'Last 3 Months' },
        { id: '1m', label: 'Last 1 Month' },
    ];

    return (
        <div className="time-filter-container">
            {periods.map(p => (
                <button
                    key={p.id}
                    className={`time-filter-btn ${selectedPeriod === p.id ? 'active' : ''}`}
                    onClick={() => onPeriodChange(p.id)}
                >
                    {p.label}
                </button>
            ))}
        </div>
    );
};

const HomeView = () => {
    const [incomeSankeyData, setIncomeSankeyData] = useState({ nodes: [], links: [] });
    const [sankeyLoading, setSankeyLoading] = useState(true);
    const [selectedPeriod, setSelectedPeriod] = useState('all');

    useEffect(() => {
        const fetchSankeyData = async () => {
            try {
                setSankeyLoading(true);
                const response = await fetch(`/api/sankey/income?period=${selectedPeriod}`);
                if (!response.ok) throw new Error('Failed to fetch income sankey');
                const data = await response.json();
                setIncomeSankeyData(data);
            } catch (error) {
                console.error(error);
            } finally {
                setSankeyLoading(false);
            }
        };
        fetchSankeyData();
    }, [selectedPeriod]);

    const isChartVisible = !sankeyLoading && incomeSankeyData && incomeSankeyData.links.length > 0;

    return (
        <>
            <NetWorthHero />
            
            <div className="card sankey-container-card"> 
                <div className="sankey-header">
                    <h2>Income → Uses of Money</h2>
                    <TimeFilter selectedPeriod={selectedPeriod} onPeriodChange={setSelectedPeriod} />
                </div>
                {sankeyLoading ? (
                    <p>Loading chart data...</p>
                ) : isChartVisible ? (
                    <SankeyChart data={incomeSankeyData} />
                ) : (
                    <p>No transaction data available for the selected period. Please import a transactions CSV file.</p>
                )}
            </div>
            
            <div className="card">
                <h2>Portfolio Return Waterfall</h2>
                <MockSankey type="returns" />
            </div>
        </>
    );
};

export default HomeView;
