import { useState, useEffect } from 'react';
import SankeyChart from '../SankeyChart';
import TimeFilter from './TimeFilter';
import PieChart from './PieChart';
import CapitalFlowTable from './CapitalFlowTable';
import TaxRateSummaryTable from './TaxRateSummaryTable';
import AccountSummaryTable from './AccountSummaryTable';
import ModeSelector from './ModeSelector';
import './HomeView.css';
import { useMode } from '../context/ModeContext';

const NetWorthHero = () => {
    const { mode } = useMode();
    const [data, setData] = useState({ liquid: 0, total: 0 });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                setLoading(true);
                const response = await fetch(`/api/portfolio/summary?mode=${mode}`);
                if (!response.ok) throw new Error('Failed to fetch summary');
                const result = await response.json();
                // 'total_net_worth' includes RE equity + portfolio market value
                setData({
                    liquid: result.total_market_value,
                    total: result.total_net_worth
                });
            } catch (error) {
                console.error('Error fetching net worth:', error);
                setData({ liquid: 0, total: 0 });
            } finally {
                setLoading(false);
            }
        };
        fetchSummary();
    }, [mode]);

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value || 0);

    return (
        <div className="net-worth-hero">
            <div className="hero-grid">
                <div className="hero-section liquid">
                    <h2>Liquid Portfolio</h2>
                    <p className="value">{loading ? '...' : formatCurrency(data.liquid)}</p>
                    <p className="timestamp">Investments & Holdings</p>
                </div>
                <div className="hero-section total">
                    <h2>Total Net Worth (Inc. Real Estate)</h2>
                    <p className="value">{loading ? '...' : formatCurrency(data.total)}</p>
                    <p className="timestamp">Including Property Equity</p>
                </div>
            </div>
        </div>
    );
};

const HomeView = ({ navigateTo }) => {
    const { mode } = useMode();
    const [capitalFlowData, setCapitalFlowData] = useState({ nodes: [], links: [] });
    const [sankeyLoading, setSankeyLoading] = useState(true);
    const [selectedPeriod, setSelectedPeriod] = useState('all');
    const [portfolioAllocation, setPortfolioAllocation] = useState({ chartData: [], tableData: [] });
    const [allocationLoading, setAllocationLoading] = useState(true);

    useEffect(() => {
        const fetchSankeyData = async () => {
            try {
                setSankeyLoading(true);
                const response = await fetch(`/api/sankey/home?period=${selectedPeriod}`);
                if (!response.ok) throw new Error('Failed to fetch Capital Flow data');
                const sankeyData = await response.json();
                setCapitalFlowData(sankeyData);
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
                const response = await fetch(`/api/analysis/portfolio-allocation?mode=${mode}`);
                if (!response.ok) throw new Error('Failed to fetch portfolio allocation');
                setPortfolioAllocation(await response.json());
            } catch (error) {
                console.error(error);
            } finally {
                setAllocationLoading(false);
            }
        };
        fetchAllocationData();
    }, [mode]);

    const handleSankeyNodeClick = (node) => {
        const { id } = node;
        const nonFilterable = ["Total Inflows", "Consumption", "Net Savings", "Other Expenses"];
        if (nonFilterable.includes(id)) return;

        let filters = { period: selectedPeriod };
        
        if (id === 'Operational Income') {
            filters.cashflow_type = 'Income';
        } else if (id === 'Portfolio Yield') {
            filters.cashflow_type = 'Investment';
        } else {
            filters.category = id;
        }

        navigateTo('Cashflow', filters);
    };

    return (
        <div className="home-view-container">
            <ModeSelector /> 
            <NetWorthHero />
            
            <div className="card sankey-container-card">
                <div className="sankey-header">
                    <h2>Capital Flow & Expense Breakdown</h2>
                    <TimeFilter selectedPeriod={selectedPeriod} onPeriodChange={setSelectedPeriod} />
                </div>
                {sankeyLoading ? <p>Loading chart data...</p> : 
                 capitalFlowData?.links.length > 0 ? <SankeyChart data={capitalFlowData} onNodeClick={handleSankeyNodeClick} /> : 
                 <p>No transaction data for this period.</p>}
            </div>

            <CapitalFlowTable period={selectedPeriod} />

            <div className="card">
                <h2>Portfolio Allocation</h2>
                {allocationLoading ? <p>Loading allocation data...</p> : 
                 portfolioAllocation?.chartData.length > 0 ? 
                    <div className="allocation-container">
                        <div className="pie-chart-wrapper"><PieChart data={portfolioAllocation.chartData} /></div>
                    </div> : 
                    <p>No holdings data with asset types found.</p>}
            </div>
            
            {/* New Table: Source of Truth for Forecasting */}
            <AccountSummaryTable />
            
            <TaxRateSummaryTable />
        </div>
    );
};

export default HomeView;
