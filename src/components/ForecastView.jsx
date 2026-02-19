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
                tooltip={({ point }) => (
                    <div
                        style={{
                            background: '#222',
                            padding: '9px 12px',
                            border: '1px solid #444',
                            borderRadius: '4px',
                            color: '#fff',
                            fontSize: '0.9em'
                        }}
                    >
                        <strong>Age {point.data.x}</strong>
                        <br />
                        {point.serieId}: <span style={{ color: point.serieColor }}>{formatCurrency(point.data.y)}</span>
                    </div>
                )}
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

    const deferredSeries = {
        id: "Tax-Deferred",
        data: data.map(d => ({ x: d.age, y: d.bucket_deferred }))
    };
    const taxableSeries = {
        id: "Taxable",
        data: data.map(d => ({ x: d.age, y: d.bucket_taxable }))
    };
    const rothSeries = {
        id: "Roth/Exempt",
        data: data.map(d => ({ x: d.age, y: d.bucket_roth }))
    };
    const realEstateSeries = {
        id: "Real Estate",
        data: data.map(d => ({ x: d.age, y: d.real_estate_equity }))
    };

    return (
        <div style={{ height: '300px' }}>
            <ResponsiveLine
                data={[realEstateSeries, rothSeries, deferredSeries, taxableSeries]}
                margin={{ top: 20, right: 20, bottom: 50, left: 70 }}
                xScale={{ type: 'linear', min: 'auto', max: 'auto' }}
                yScale={{ type: 'linear', stacked: true }}
                axisBottom={{ legend: 'Age', legendOffset: 36, legendPosition: 'middle' }}
                axisLeft={{ format: value => `$${value / 1000000}M` }}
                colors={['#00f2fe', '#4facfe', '#05c46b', '#ffc048']} 
                enableArea={true}
                areaOpacity={0.6}
                enablePoints={false}
                useMesh={true}
                tooltip={({ point }) => (
                    <div
                        style={{
                            background: '#222',
                            padding: '9px 12px',
                            border: '1px solid #444',
                            borderRadius: '4px',
                            color: '#fff',
                            fontSize: '0.9em'
                        }}
                    >
                        <strong>Age {point.data.x}</strong>
                        <br />
                        {point.serieId}: <span style={{ color: point.serieColor }}>{formatCurrency(point.data.y)}</span>
                    </div>
                )}
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
                    legend: 'Annual Outflows',
                    legendPosition: 'middle',
                    legendOffset: -60
                }}
                enableLabel={false}
                tooltip={({ id, value, indexValue }) => (
                    <div style={{ padding: 12, background: '#222', color: '#fff', border: '1px solid #555' }}>
                        <strong>Age {indexValue}</strong><br />
                        {id}: {formatCurrency(value)}
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

// --- NEW COMPONENT: Flight Recorder Table ---
const FlightRecorderTable = ({ data }) => {
    const [isOpen, setIsOpen] = useState(false);

    if (!data || data.length === 0) return null;

    return (
        <div className="settings-panel" style={{marginTop: '2rem'}}>
            <div 
                style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer'}}
                onClick={() => setIsOpen(!isOpen)}
            >
                <h3>Flight Recorder (Year-by-Year Telemetry)</h3>
                <span>{isOpen ? '▲' : '▼'}</span>
            </div>
            
            {isOpen && (
                <div style={{maxHeight: '500px', overflow: 'auto', marginTop: '1rem', border: '1px solid #444'}}>
                    <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.85em'}}>
                        <thead style={{position: 'sticky', top: 0, background: '#333'}}>
                            <tr>
                                <th style={{padding: '8px', textAlign: 'left'}}>Year</th>
                                <th style={{padding: '8px', textAlign: 'left'}}>Age</th>
                                <th style={{padding: '8px', textAlign: 'right'}}>Total Income</th>
                                <th style={{padding: '8px', textAlign: 'right'}}>Total Expense</th>
                                <th style={{padding: '8px', textAlign: 'right', color: '#ccc'}}>RMDs</th>
                                <th style={{padding: '8px', textAlign: 'right', color: '#ffc048'}}>Taxable Bal</th>
                                <th style={{padding: '8px', textAlign: 'right', color: '#05c46b'}}>Deferred Bal</th>
                                <th style={{padding: '8px', textAlign: 'right', color: '#4facfe'}}>Roth Bal</th>
                                <th style={{padding: '8px', textAlign: 'right'}}>End Net Worth</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.map(row => (
                                <tr key={row.year} style={{borderBottom: '1px solid #444'}}>
                                    <td style={{padding: '8px'}}>{row.year}</td>
                                    <td style={{padding: '8px'}}>{row.age}</td>
                                    <td style={{padding: '8px', textAlign: 'right', fontFamily: 'monospace', color: '#4facfe'}}>
                                        {formatCurrency(row.total_income)}
                                    </td>
                                    <td style={{padding: '8px', textAlign: 'right', fontFamily: 'monospace', color: '#ff6b6b'}}>
                                        {formatCurrency(row.total_expenses)}
                                    </td>
                                    <td style={{padding: '8px', textAlign: 'right', fontFamily: 'monospace', color: row.rmd_event > 0 ? '#E2B254' : '#555'}}>
                                        {row.rmd_event > 0 ? formatCurrency(row.rmd_event) : '-'}
                                    </td>
                                    <td style={{padding: '8px', textAlign: 'right', fontFamily: 'monospace'}}>
                                        {formatCurrency(row.bucket_taxable)}
                                    </td>
                                    <td style={{padding: '8px', textAlign: 'right', fontFamily: 'monospace'}}>
                                        {formatCurrency(row.bucket_deferred)}
                                    </td>
                                    <td style={{padding: '8px', textAlign: 'right', fontFamily: 'monospace'}}>
                                        {formatCurrency(row.bucket_roth)}
                                    </td>
                                    <td style={{padding: '8px', textAlign: 'right', fontFamily: 'monospace', fontWeight: 'bold'}}>
                                        {formatCurrency(row.total_net_worth)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
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
            <div className="setting-group">
                <label>Est. Withdrawal Tax Rate (0.15 = 15%)</label>
                <p style={{fontSize:'0.7em', color:'#aaa', margin:'0 0 5px'}}>Accounts for taxes when selling assets to cover deficits.</p>
                <input type="number" name="withdrawal_tax_rate" step="0.01" value={config.withdrawal_tax_rate !== undefined ? config.withdrawal_tax_rate : 0.15} onChange={handleChange} onBlur={onSave} />
            </div>
        </div>
    );
};

const ResidenceSaleConfig = ({ config, setConfig, onSave }) => {
    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setConfig(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    return (
        <div className="settings-panel" style={{marginTop: '2rem'}}>
            <h3>Principal Residence Sale Strategy</h3>
            <p style={{fontSize: '0.8em', color: '#aaa', marginTop: '-0.5rem'}}>
                Simulate selling your primary home and moving equity into liquid investments.
            </p>
            <div className="setting-group" style={{display: 'flex', alignItems: 'center', marginBottom: '1rem'}}>
                <input 
                    type="checkbox" 
                    id="residence_sale_enabled"
                    name="residence_sale_enabled"
                    checked={config.residence_sale_enabled || false} 
                    onChange={handleChange} 
                    onBlur={onSave}
                    style={{width: 'auto', marginRight: '0.5rem'}}
                />
                <label htmlFor="residence_sale_enabled" style={{margin: 0, cursor: 'pointer', color: '#fff'}}>Enable Sale Strategy</label>
            </div>
            
            {config.residence_sale_enabled && (
                <div className="setting-group">
                    <label>Sale Year (e.g. 2040)</label>
                    <input 
                        type="number" 
                        name="residence_sale_year" 
                        value={config.residence_sale_year || ''} 
                        onChange={handleChange} 
                        onBlur={onSave} 
                        placeholder="YYYY"
                    />
                </div>
            )}
        </div>
    );
};

const PhaseConfiguration = ({ config, setConfig, onSave }) => {
    const [allCategories, setAllCategories] = useState([]);

    useEffect(() => {
        fetch('/api/filter-options')
            .then(r => r.json())
            .then(d => setAllCategories(d.categories || []));
    }, []);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setConfig(prev => ({ ...prev, [name]: value }));
    };

    // Helper to update multipliers deeply
    const updateMultiplier = (category, phase, value) => {
        const currentMultipliers = config.phase_multipliers || {};
        const catConfig = currentMultipliers[category] || { go: 100, slow: 80, no: 20 };
        
        // Scotty Fix: Allow empty string to pass through so the user can clear the field 
        // without it snapping to 0. We convert to int only if it's not empty.
        const valToStore = value === '' ? '' : parseInt(value);

        const updated = {
            ...currentMultipliers,
            [category]: { ...catConfig, [phase]: valToStore }
        };
        
        setConfig(prev => ({ ...prev, phase_multipliers: updated }));
    };

    // Safe getter that respects 0 as a valid value but defaults if undefined
    const getVal = (cat, phase) => {
        const val = config.phase_multipliers?.[cat]?.[phase];
        // If value is explicitly set (even if it's 0 or empty string), return it.
        if (val !== undefined && val !== null) {
            return val;
        }
        // Default fallbacks if not set in config yet
        if (phase === 'go') return 100;
        if (phase === 'slow') return 80;
        if (phase === 'no') return 20;
        return 100;
    }

    return (
        <div className="settings-panel" style={{marginTop: '2rem'}}>
            <h3>"Go Slow No" Phase Config</h3>
            <div style={{display:'flex', gap:'1rem'}}>
                <div className="setting-group" style={{flex:1}}>
                    <label>Retirement Age (Start Slow Go)</label>
                    <input type="number" name="retirement_age" value={config.retirement_age || ''} onChange={handleChange} onBlur={onSave} />
                </div>
                <div className="setting-group" style={{flex:1}}>
                    <label>No Go Age (Low Energy)</label>
                    <input type="number" name="nogo_age" value={config.nogo_age || ''} onChange={handleChange} onBlur={onSave} />
                </div>
            </div>
            
            <h4>Category Consumption Multipliers (%)</h4>
            <p style={{fontSize: '0.8em', color: '#aaa', marginTop: '-0.5rem'}}>Controls spending intensity in each phase. 100 = 100%.</p>
            <div style={{maxHeight: '200px', overflowY: 'auto', border: '1px solid #444', borderRadius: '4px'}}>
                <table style={{width: '100%', fontSize: '0.9em', borderCollapse: 'collapse'}}>
                    <thead>
                        <tr style={{background: '#333', textAlign: 'left'}}>
                            <th style={{padding: '5px'}}>Category</th>
                            <th style={{padding: '5px'}}>Go</th>
                            <th style={{padding: '5px'}}>Slow</th>
                            <th style={{padding: '5px'}}>No</th>
                        </tr>
                    </thead>
                    <tbody>
                        {allCategories.map(cat => (
                            <tr key={cat} style={{borderBottom: '1px solid #444'}}>
                                <td style={{padding: '5px'}}>{cat}</td>
                                <td style={{padding: '5px'}}>
                                    <input 
                                        type="number" style={{width: '50px', padding: '2px'}} 
                                        value={getVal(cat, 'go')} 
                                        onChange={(e) => updateMultiplier(cat, 'go', e.target.value)} 
                                        onBlur={onSave}
                                    />
                                </td>
                                <td style={{padding: '5px'}}>
                                    <input 
                                        type="number" style={{width: '50px', padding: '2px'}} 
                                        value={getVal(cat, 'slow')} 
                                        onChange={(e) => updateMultiplier(cat, 'slow', e.target.value)} 
                                        onBlur={onSave}
                                    />
                                </td>
                                <td style={{padding: '5px'}}>
                                    <input 
                                        type="number" style={{width: '50px', padding: '2px'}} 
                                        value={getVal(cat, 'no')} 
                                        onChange={(e) => updateMultiplier(cat, 'no', e.target.value)} 
                                        onBlur={onSave}
                                    />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

const BaseColCalculator = ({ selectedCategories, onSelectionChange, calculatedTotal, lookbackYears, onLookbackChange }) => {
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
                    <div className="setting-group" style={{marginBottom: '1rem', borderBottom: '1px solid #444', paddingBottom: '1rem'}}>
                         <label>Averaging Period (Lookback)</label>
                         <select 
                            value={lookbackYears || 1} 
                            onChange={(e) => onLookbackChange(parseInt(e.target.value))}
                            style={{width: '100%', padding: '0.5rem', background: '#222', color: '#fff', border: '1px solid #666', borderRadius: '4px'}}
                         >
                             <option value={1}>Last 12 Months (1 Year)</option>
                             <option value={2}>Last 24 Months (2 Year Avg)</option>
                         </select>
                         <p style={{fontSize: '0.8em', color: '#ff9a9a', marginTop: '0.5rem', fontStyle: 'italic'}}>
                             * Please don't use partial years. Ensure you have full data for the selected period.
                         </p>
                    </div>

                    <p style={{fontSize: '0.9em', color: '#999', marginTop: 0}}>Select categories to include in Base CoL.</p>
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
    const [newItem, setNewItem] = useState({ name: '', amount: '', start_year: new Date().getFullYear(), is_recurring: false, category: '' });
    const [categories, setCategories] = useState([]);

    useEffect(() => {
        fetch('/api/filter-options')
            .then(r => r.json())
            .then(d => setCategories(d.categories || []));
    }, []);

    const handleSubmit = (e) => {
        e.preventDefault();
        onAdd(newItem);
        setNewItem({ name: '', amount: '', start_year: new Date().getFullYear(), is_recurring: false, category: '' });
    };

    return (
        <div className="budget-panel">
            <h3>Discretionary Budget (Big Ticket Items)</h3>
            <form onSubmit={handleSubmit} className="budget-form">
                <input type="text" placeholder="Item Name" value={newItem.name} onChange={e => setNewItem({...newItem, name: e.target.value})} required />
                <input type="number" placeholder="Amount" value={newItem.amount} onChange={e => setNewItem({...newItem, amount: e.target.value})} required />
                <input type="number" placeholder="Start Year" value={newItem.start_year} onChange={e => setNewItem({...newItem, start_year: e.target.value})} required />
                
                <input 
                    type="text" placeholder="Category (Optional)" 
                    list="disc-cat-list" 
                    value={newItem.category} 
                    onChange={e => setNewItem({...newItem, category: e.target.value})} 
                />
                <datalist id="disc-cat-list">
                    {categories.map(c => <option key={c} value={c} />)}
                </datalist>

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
                        <th>Category</th>
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
                            <td>{item.category || '-'}</td>
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
    const [alerts, setAlerts] = useState([]);
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
            setAlerts(data.alerts || []);
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

    const handleLookbackChange = (years) => {
        setConfig(prev => ({ ...prev, base_col_lookback_years: years }));
        // Note: saveConfig() will be called automatically if we hook this right, 
        // but here we just update local state and let the user interaction trigger save
        // Actually, let's trigger save explicitly or rely on a useEffect.
        // Simpler: Just update state, and call saveConfig directly after state update if we were class based.
        // Better: trigger the PUT immediately.
        fetch('/api/forecast/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...config,
                base_col_categories: baseColCategories,
                base_col_lookback_years: years
            })
        }).then(() => {
             setConfig(prev => ({ ...prev, base_col_lookback_years: years }));
             setRefreshKey(k => k + 1);
        });
    };

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
                {alerts.length > 0 && (
                    <div style={{background: '#5a2a2a', color: '#ffc048', padding: '1rem', marginBottom: '1rem', borderRadius: '4px'}}>
                        <strong>Warning:</strong> {alerts.map((a, i) => <div key={i}>{a}</div>)}
                    </div>
                )}
                <RunwayChart data={simulationData} />
                <FlightRecorderTable data={simulationData} />
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
                    <PhaseConfiguration
                        config={config}
                        setConfig={setConfig}
                        onSave={saveConfig}
                    />
                    <ResidenceSaleConfig
                        config={config}
                        setConfig={setConfig}
                        onSave={saveConfig}
                    />
                    <BaseColCalculator 
                        selectedCategories={baseColCategories} 
                        onSelectionChange={setBaseColCategories} 
                        calculatedTotal={baseColTotal} 
                        lookbackYears={config.base_col_lookback_years}
                        onLookbackChange={handleLookbackChange}
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