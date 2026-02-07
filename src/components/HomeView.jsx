import { useState, useEffect } from 'react';
import SankeyChart from '../SankeyChart';
import TimeFilter from './TimeFilter';
import PieChart from './PieChart';
import CapitalFlowTable from './CapitalFlowTable';
import InvestmentSummaryTable from './InvestmentSummaryTable';
import TaxRateSummaryTable from './TaxRateSummaryTable';
import './HomeView.css';
import { useMode } from '../context/ModeContext';

const NetWorthHero = () => {
    const { mode } = useMode();
    const [netWorth, setNetWorth] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                setLoading(true);
                const response = await fetch(`/api/portfolio/summary?mode=${mode}`);
                if (!response.ok) throw new Error('Failed to fetch summary');
                const data = await response.json();
                setNetWorth(data.total_market_value);
            } catch (error) {
                console.error('Error fetching net worth:', error);
                setNetWorth(0);
            } finally {
                setLoading(false);
            }
        };
        fetchSummary();
    }, [mode]);

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value || 0);

    return (
        <div className="net-worth-hero">
            <h2>Latest Net Worth</h2>
            <p className="value">{loading ? 'Calculating...' : formatCurrency(netWorth)}</p>
            <p className="timestamp">As of latest holdings import</p>
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
            // Assume any other clickable node is an expense category or income category
            // We'll need a way to differentiate. For now, assume expense.
            // A better approach would be to get the node's type from the backend.
            filters.category = id;
        }

        navigateTo('Cashflow', filters);
    };

    return (
        <>
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
            
            <InvestmentSummaryTable period={selectedPeriod} />

            <TaxRateSummaryTable />
        </>
    );
};

export default HomeView;
