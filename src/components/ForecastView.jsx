import { useState, useEffect } from 'react';
import { ResponsiveLine } from '@nivo/line';
import { ResponsiveBar } from '@nivo/bar';
import './ForecastView.css';

const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
}).format(value || 0);

// --- CHARTS ---

const RunwayChart = ({ data }) => {
    if (!data || data.length === 0) return <p>No simulation data available.</p>;

    const netWorthSeries = {
        id: "Total Net Worth",
        data: data.map(d => ({ x: d.age, y: d.total_net_worth }))
    };

    return (
        <div style={{ height: '400px' }}>
            <ResponsiveLine
                data={[netWorthSeries]}
                margin={{ top: 20, right: 110, bottom: 50, left: 80 }}
                xScale={{ type: 'linear', min: 'auto', max: 'auto' }}
                yScale={{ type: 'linear', min: 'auto', max: 'auto' }}
                axisBottom={{ 
                    legend: 'Age', legendOffset: 36, legendPosition: 'middle', 
                    tickSize: 5, tickPadding: 5 
                }}
                axisLeft={{ 
                    legend: 'Net Worth ($)', legendOffset: -70, legendPosition: 'middle', 
                    format: value => `$${value / 1000000}M`
                }}
                colors={['#E2B254']} // Gold for Net Worth
                lineWidth={3}
                pointSize={4}
                pointColor={{ theme: 'background' }}
                pointBorderWidth={2}
                pointBorderColor={{ from: 'serieColor' }}
                useMesh={true}
                enableArea={true}
                areaOpacity={0.1}
                theme={{
                    axis: { 
                        ticks: { text: { fill: '#bbb' } }, 
                        legend: { text: { fill: '#bbb' } } 
                    },
                    grid: { line: { stroke: '#444' } },
                    tooltip: { container: { background: '#222', color: '#fff' } }
                }}
            />
        </div>
    );
};

const AssetCompositionChart = ({ data }) => {
    // Stacked Area Chart for Assets
    if (!data || data.length === 0) return null;

    const liquidSeries = {
        id: "Liquid Portfolio",
        data: data.map(d => ({ x: d.age, y: d.liquid_assets }))
    };
    const realEstateSeries = {
        id: "Real Estate Equity",
        data: data.map(d => ({ x: d.age, y: d.real_estate_equity }))
    };

    return (
        <div style={{ height: '300px' }}>
            <ResponsiveLine
                data={[liquidSeries, realEstateSeries]}
                margin={{ top: 20, right: 20, bottom: 50, left: 70 }}
                xScale={{ type: 'linear' }}
                yScale={{ type: 'linear', stacked: true }}
                axisBottom={{ legend: 'Age', legendOffset: 36, legendPosition: 'middle' }}
                axisLeft={{ format: value => `$${value / 1000000}M` }}
                colors={['#4facfe', '#00f2fe']} // Blue gradients
                enableArea={true}
                areaOpacity={0.6}
                enablePoints={false}
                useMesh={true}
                theme={{
                    axis: { ticks: { text: { fill: '#bbb' } }, legend: { text: { fill: '#bbb' } } },
                    grid: { line: { stroke: '#444' } },
                    tooltip: { container: { background: '#222', color: '#fff' } }
                }}
            />
        </div>
    );
};

const ExpenseCompositionChart = ({ data }) => {
    // Stacked Bar Chart for Expenses
    if (!data || data.length === 0) return null;

    return (
        <div style={{ height: '300px' }}>
            <ResponsiveBar
                data={data}
                keys={['base_col_expense', 'discretionary_expense']}
                indexBy="age"
                margin={{ top: 20, right: 20, bottom: 50, left: 70 }}
                padding={0.1}
                colors={['#ff6b6b', '#feca57']}
                axisBottom={{ legend: 'Age', legendOffset: 36, legendPosition: 'middle' }}
                axisLeft={{ 
                    format: value => `$${value / 1000}k`,
                    legend: 'Annual Expenses',
                    legendPosition: 'middle',
                    legendOffset: -60
                }}
                enableLabel={false}
                tooltip={({ id, value, indexValue }) => (
                    <div style={{ padding: 12, background: '#222', color: '#fff', border: '1px solid #555' }}>
                        <strong>Age {indexValue}</strong><br />
                        {id === 'base_col_expense' ? 'Base CoL' : 'Discretionary'}: {formatCurrency(value)}
                    </div>
                )}
                theme={{
                    axis: { ticks: { text: { fill: '#bbb' } }, legend: { text: { fill: '#bbb' } } },
                    grid: { line: { stroke: '#444' } }
                }}
            />
        </div>
    );
};

// --- COMPONENTS ---

const ForecastSettings = ({ config, setConfig, onSave }) => {
    const handleChange = (e) => {
        const { name, value } = e.target;
        setConfig(prev => ({ ...prev, [name]: value }));
    };

    return (
        <div className="settings-panel">
            <h3>Flight Parameters</h3>
            <div className="setting-group">
                <label>Birth Year</label>
                <input type="number" name="birth_year" value={config.birth_year || ''} onChange={handleChange} onBlur={onSave} />
            </div>
            <div className="setting-group">
                <label>Inflation Rate (0.03 = 3%)</label>
                <input type="number" name="inflation_rate" step="0.001" value={config.inflation_rate || ''} onChange={handleChange} onBlur={onSave} />
            </div>
            <div className="setting-group">
                <label>Portfolio Return Rate (0.05 = 5%)</label>
                <input type="number" name="return_rate" step="0.001" value={config.return_rate || ''} onChange={handleChange} onBlur={onSave} />
            </div>
        </div>
    );
};

const BaseColCalculator = ({ selectedCategories, onSelectionChange, calculatedTotal }) => {
    const [allCategories, setAllCategories] = useState([]);
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        fetch('/api/filter-options')
            .then(r => r.json())
            .then(d => setAllCategories(d.categories || []));
    }, []);

    const handleToggle = (cat) => {
        const newSelection = selectedCategories.includes(cat)
            ? selectedCategories.filter(c => c !== cat)
            : [...selectedCategories, cat];
        onSelectionChange(newSelection);
    };

    return (
        <div className="col-calculator-panel">
            <div className={`col-header ${isOpen ? 'open' : ''}`} onClick={() => setIsOpen(!isOpen)}>
                <h3>Base Cost of Living (Year 0)</h3>
                <div style={{display:'flex', alignItems:'center'}}>
                    <span className="total-badge">{formatCurrency(calculatedTotal)}</span>
                    <span className="toggle-icon">▼</span>
                </div>
            </div>
            
            {isOpen && (
                <div className="col-content">
                    <p style={{fontSize: '0.9em', color: '#999', marginTop: 0}}>Select categories based on last 12 months actuals.</p>
                    <div className="col-selector-list">
                        {allCategories.map(cat => (
                            <div key={cat} className="col-item">
                                <input 
                                    type="checkbox" 
                                    id={`col-${cat}`}
                                    checked={selectedCategories.includes(cat)}
                                    onChange={() => handleToggle(cat)}
                                />
                                <label htmlFor={`col-${cat}`}>{cat}</label>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

const DiscretionaryBudget = ({ items, onAdd, onDelete }) => {
    const [newItem, setNewItem] = useState({ name: '', amount: '', start_year: new Date().getFullYear(), is_recurring: false });

    const handleSubmit = (e) => {
        e.preventDefault();
        onAdd(newItem);
        setNewItem({ name: '', amount: '', start_year: new Date().getFullYear(), is_recurring: false });
    };

    return (
        <div className="budget-panel">
            <h3>Discretionary Budget (Big Ticket Items)</h3>
            <form onSubmit={handleSubmit} className="budget-form">
                <input type="text" placeholder="Item Name" value={newItem.name} onChange={e => setNewItem({...newItem, name: e.target.value})} required />
                <input type="number" placeholder="Amount" value={newItem.amount} onChange={e => setNewItem({...newItem, amount: e.target.value})} required />
                <input type="number" placeholder="Start Year" value={newItem.start_year} onChange={e => setNewItem({...newItem, start_year: e.target.value})} required />
                <label style={{display:'flex', alignItems:'center', color: '#ccc'}}>
                    <input type="checkbox" checked={newItem.is_recurring} onChange={e => setNewItem({...newItem, is_recurring: e.target.checked})} style={{width:'auto', marginRight:'5px'}} />
                    Recurring?
                </label>
                <button type="submit">Add Item</button>
            </form>
            
            <table className="budget-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Amount</th>
                        <th>Start Year</th>
                        <th>Recurring</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {items.map(item => (
                        <tr key={item.item_id}>
                            <td>{item.name}</td>
                            <td>{formatCurrency(item.amount)}</td>
                            <td>{item.start_year}</td>
                            <td>{item.is_recurring ? 'Yes' : 'No'}</td>
                            <td><button className="delete-btn" onClick={() => onDelete(item.item_id)}>✕</button></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

// --- MAIN VIEW ---

const ForecastView = () => {
    const [config, setConfig] = useState({});
    const [baseColCategories, setBaseColCategories] = useState([]);
    const [baseColTotal, setBaseColTotal] = useState(0);
    const [simulationData, setSimulationData] = useState([]);
    const [budgetItems, setBudgetItems] = useState([]);
    const [refreshKey, setRefreshKey] = useState(0);

    // Initial Load
    useEffect(() => {
        fetch('/api/forecast/config').then(r => r.json()).then(data => {
            setConfig(data);
            setBaseColCategories(data.base_col_categories || []);
        });
        
        fetch('/api/forecast/discretionary').then(r => r.json()).then(setBudgetItems);
    }, []);

    // Recalculate Simulation whenever inputs change
    useEffect(() => {
        fetch('/api/forecast/simulation').then(r => r.json()).then(data => {
            setSimulationData(data.simulation_series);
            if (data.settings && data.settings.starting_base_col) {
                setBaseColTotal(data.settings.starting_base_col);
            }
        });
    }, [refreshKey, config]); 

    const saveConfig = async () => {
        await fetch('/api/forecast/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...config,
                base_col_categories: baseColCategories
            })
        });
        setRefreshKey(k => k + 1);
    };

    // Auto-save base categories when they change
    useEffect(() => {
        if (baseColCategories.length > 0) {
            saveConfig();
        }
    }, [baseColCategories]);

    const handleAddItem = async (item) => {
        await fetch('/api/forecast/discretionary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item)
        });
        const res = await fetch('/api/forecast/discretionary');
        setBudgetItems(await res.json());
        setRefreshKey(k => k + 1);
    };

    const handleDeleteItem = async (id) => {
        await fetch(`/api/forecast/discretionary/${id}`, { method: 'DELETE' });
        const res = await fetch('/api/forecast/discretionary');
        setBudgetItems(await res.json());
        setRefreshKey(k => k + 1);
    };

    return (
        <div className="forecast-view-container">
            <div className="chart-panel">
                <h2>The Runway (Age 95 Horizon)</h2>
                <RunwayChart data={simulationData} />
            </div>
            
            <div className="charts-row">
                <div className="chart-sub-panel">
                    <h3>Asset Composition (Accumulation)</h3>
                    <AssetCompositionChart data={simulationData} />
                </div>
                <div className="chart-sub-panel">
                    <h3>Expense Profile (Outflows)</h3>
                    <ExpenseCompositionChart data={simulationData} />
                </div>
            </div>

            <div className="forecast-grid">
                <div className="left-column">
                    <ForecastSettings 
                        config={config} 
                        setConfig={setConfig} 
                        onSave={saveConfig} 
                    />
                    <BaseColCalculator 
                        selectedCategories={baseColCategories} 
                        onSelectionChange={setBaseColCategories} 
                        calculatedTotal={baseColTotal} 
                    />
                </div>
                
                <div className="right-column">
                    <DiscretionaryBudget 
                        items={budgetItems} 
                        onAdd={handleAddItem} 
                        onDelete={handleDeleteItem} 
                    />
                </div>
            </div>
        </div>
    );
};

export default ForecastView;
