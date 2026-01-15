import { useState, useEffect } from 'react';
import SankeyChart from '../SankeyChart';
import MockSankey from './MockSankey';
import TimeFilter from './TimeFilter';
import PieChart from './PieChart';
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

const AllocationTable = ({ tableData, formatCurrency }) => {
    return (
        <div className="allocation-table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Value</th>
                        <th>% of Portfolio</th>
                    </tr>
                </thead>
                <tbody>
                    {tableData.map(row => (
                        <tr key={row.categoryName}>
                            <td>{row.categoryName}</td>
                            <td>{formatCurrency(row.value)}</td>
                            <td>{row.percentage}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

const HomeView = ({ navigateTo }) => {
    const [incomeSankeyData, setIncomeSankeyData] = useState({ nodes: [], links: [] });
    const [sankeyLoading, setSankeyLoading] = useState(true);
    const [selectedPeriod, setSelectedPeriod] = useState('all');
    const [portfolioAllocation, setPortfolioAllocation] = useState({ chartData: [], tableData: [] });
    const [allocationLoading, setAllocationLoading] = useState(true);

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

    useEffect(() => {
        const fetchAllocationData = async () => {
            try {
                setAllocationLoading(true);
                const response = await fetch('/api/analysis/portfolio-allocation');
                if (!response.ok) throw new Error('Failed to fetch portfolio allocation');
                const data = await response.json();
                setPortfolioAllocation(data);
            } catch (error) {
                console.error(error);
            } finally {
                setAllocationLoading(false);
            }
        };

        fetchAllocationData();
    }, []);

    const handleSankeyNodeClick = (node) => {
        const { id } = node;
        let filters = { period: selectedPeriod };

        const nonFilterableNodes = ["Income", "Available Funds", "Net Surplus", "Net Deficit"];
        if (nonFilterableNodes.includes(id)) {
            console.log(`Drill-down on structural node '${id}' is disabled.`);
            return;
        }

        if (id === 'Capital Expenditure') {
            filters.cashflow_type = 'Capital Expenditure';
        } else if (id.endsWith('(Expense)')) {
            filters.category = id.replace(' (Expense)', '');
        } else {
            filters.category = id;
        }

        console.log(`Navigating to Cashflow view with filters:`, filters);
        navigateTo('Cashflow', filters);
    };

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value || 0);

    const isSankeyVisible = !sankeyLoading && incomeSankeyData && incomeSankeyData.links.length > 0;
    const isAllocationVisible = !allocationLoading && portfolioAllocation.chartData && portfolioAllocation.chartData.length > 0;

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
                ) : isSankeyVisible ? (
                    <SankeyChart data={incomeSankeyData} onNodeClick={handleSankeyNodeClick} />
                ) : (
                    <p>No transaction data available for the selected period. Please import a transactions CSV file.</p>
                )}
            </div>

            <div className="card">
                <h2>Portfolio Allocation</h2>
                {allocationLoading ? (
                    <p>Loading allocation data...</p>
                ) : isAllocationVisible ? (
                    <div className="allocation-container">
                        <div className="pie-chart-wrapper">
                            <PieChart data={portfolioAllocation.chartData} />
                        </div>
                        <AllocationTable 
                            tableData={portfolioAllocation.tableData} 
                            formatCurrency={formatCurrency} 
                        />
                    </div>
                ) : (
                    <p>No holdings data with asset types found. Please import a holdings CSV with an 'asset_type' column.</p>
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
