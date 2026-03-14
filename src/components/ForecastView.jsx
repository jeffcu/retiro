import { useState, useEffect } from 'react';
import { ResponsiveLine } from '@nivo/line';
import { ResponsiveBar } from '@nivo/bar';
import './ForecastView.css';
import { useMode } from '../context/ModeContext';

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
        <div style={{ height: '350px' }}>
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
                    legend: 'Value ($)', legendOffset: -70, legendPosition: 'middle', 
                    format: value => `$${value / 1000000}M`
                }}
                colors={['#E2B254']} 
                lineWidth={4}
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
                legends={[
                    {
                        anchor: 'bottom-right',
                        direction: 'column',
                        justify: false,
                        translateX: 100,
                        translateY: 0,
                        itemsSpacing: 0,
                        itemDirection: 'left-to-right',
                        itemWidth: 80,
                        itemHeight: 20,
                        itemOpacity: 0.75,
                        symbolSize: 12,
                        symbolShape: 'circle',
                        symbolBorderColor: 'rgba(0, 0, 0, .5)',
                        effects: [
                            {
                                on: 'hover',
                                style: {
                                    itemBackground: 'rgba(0, 0, 0, .03)',
                                    itemOpacity: 1
                                }
                            }
                        ]
                    }
                ]}
            />
        </div>
    );
};

const AssetCompositionChart = ({ data }) => {
    if (!data || data.length === 0) return null;

    const realEstateSeries = {
        id: "Real Estate Equity",
        data: data.map(d => ({ x: d.age, y: d.real_estate_equity }))
    };
    
    // Break down liquid assets into buckets for v1.9
    const deferredSeries = {
        id: "Deferred (IRA)",
        data: data.map(d => ({ x: d.age, y: d.bucket_deferred }))
    };
    
    const taxableSeries = {
        id: "Taxable",
        data: data.map(d => ({ x: d.age, y: d.bucket_taxable }))
    };
    
    const rothSeries = {
        id: "Roth",
        data: data.map(d => ({ x: d.age, y: d.bucket_roth }))
    };

    return (
        <div style={{ height: '300px' }}>
            <ResponsiveLine
                data={[realEstateSeries, taxableSeries, deferredSeries, rothSeries]}
                margin={{ top: 20, right: 20, bottom: 50, left: 70 }}
                xScale={{ type: 'linear', min: 'auto', max: 'auto' }}
                yScale={{ type: 'linear', stacked: true }}
                axisBottom={{ legend: 'Age', legendOffset: 36, legendPosition: 'middle' }}
                axisLeft={{ format: value => `$${value / 1000000}M` }}
                colors={['#05c46b', '#00f2fe', '#feca57', '#ff9ff3']} 
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

// --- INPUT COMPONENTS ---

const CollapsibleCard = ({ title, children, defaultOpen = true, className = "" }) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);
    return (
        <div className={`settings-panel ${className}`}>
            <div className="collapsible-header" onClick={() => setIsOpen(!isOpen)}>
                <h3>{title}</h3>
                <span>{isOpen ? '▲' : '▼'}</span>
            </div>
            {isOpen && <div className="forecast-collapsible-content">{children}</div>}
        </div>
    );
};

const BaseColCalculator = ({ selectedCategories, onSelectionChange, calculatedTotal, lookbackYears, onLookbackChange, sunsetDates, onSunsetChange }) => {
    const [allCategories, setAllCategories] = useState([]);

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

    const handleSunsetChange = (cat, year) => {
        onSunsetChange(cat, year);
    };

    return (
        <CollapsibleCard title="6) Base Cost of Living (CoL) Engine" className="grid-half-right">
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: '1rem', background: '#333', padding: '0.5rem', borderRadius: '4px'}}>
                 <span style={{color:'#aaa'}}>Year 0 Base:</span>
                 <span style={{fontWeight:'bold', color:'var(--gold-accent)', fontSize: '1.2em'}}>{formatCurrency(calculatedTotal)}</span>
            </div>

            <div className="setting-group">
                 <label>Averaging Period (Lookback)</label>
                 <select 
                    value={lookbackYears || 1} 
                    onChange={(e) => onLookbackChange(parseInt(e.target.value))}
                 >
                     <option value={1}>Last 12 Months (1 Year)</option>
                     <option value={2}>Last 24 Months (2 Year Avg)</option>
                 </select>
            </div>

            <p style={{fontSize: '0.8em', color: '#999'}}>Check categories to include. Set an End Year (Sunset) if expenses stop (e.g. Mortgage).</p>
            
            <div style={{maxHeight: '300px', overflowY: 'auto', border: '1px solid #444', borderRadius: '4px'}}>
                {allCategories.map(cat => {
                    const isChecked = selectedCategories.includes(cat);
                    return (
                        <div key={cat} className="col-item" style={{opacity: isChecked ? 1 : 0.6}}>
                            <div className="col-label-group">
                                <input 
                                    type="checkbox" 
                                    id={`col-${cat}`}
                                    checked={isChecked}
                                    onChange={() => handleToggle(cat)}
                                    style={{width: 'auto', marginRight: '0.5rem'}}
                                />
                                <label htmlFor={`col-${cat}`} style={{margin:0, cursor:'pointer'}}>{cat}</label>
                            </div>
                            {isChecked && (
                                <div className="col-end-year">
                                    <span>Ends:</span>
                                    <input 
                                        type="number" 
                                        placeholder="Never"
                                        value={sunsetDates?.[cat] || ''}
                                        onChange={(e) => handleSunsetChange(cat, e.target.value)}
                                        title="Enter a year (e.g. 2030) when this expense stops."
                                    />
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </CollapsibleCard>
    );
};

const DiscretionaryBudget = ({ items, onAdd, onDelete, onUpdate }) => {
    const [newItem, setNewItem] = useState({ 
        item_id: null, 
        name: '', 
        amount: '', 
        start_year: new Date().getFullYear(), 
        end_year: '', 
        is_recurring: false, 
        category: '', 
        is_enabled: true 
    });
    const [categories, setCategories] = useState([]);

    useEffect(() => {
        fetch('/api/filter-options')
            .then(r => r.json())
            .then(d => setCategories(d.categories || []));
    }, []);

    const handleSubmit = (e) => {
        e.preventDefault();
        const payload = { ...newItem };
        if (!payload.end_year) payload.end_year = null;
        if (!payload.item_id) delete payload.item_id; // Let backend generate it if new
        onAdd(payload);
        setNewItem({ item_id: null, name: '', amount: '', start_year: new Date().getFullYear(), end_year: '', is_recurring: false, category: '', is_enabled: true });
    };

    const handleRowDoubleClick = (item) => {
        setNewItem({
            item_id: item.item_id,
            name: item.name,
            amount: item.amount,
            start_year: item.start_year,
            end_year: item.end_year || '',
            is_recurring: !!item.is_recurring,
            category: item.category || '',
            is_enabled: !!item.is_enabled
        });
    };

    const handleDelete = (id) => {
        if (!id) {
            alert("Error: Item ID is missing.");
            return;
        }
        if (window.confirm("Are you sure you want to delete this forever?")) {
            onDelete(id);
        }
    };

    return (
        <CollapsibleCard title="4) Discretionary Budget (Changes)" className="grid-full">
            <p style={{fontSize: '0.9em', color: '#ccc'}}>
                Add large one-off or recurring expenses. <br/>
                <em>Double-click any item in the list to edit it. Negative amounts reduce expenses.</em>
            </p>
            <form onSubmit={handleSubmit} style={{display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: '1rem'}}>
                <div className="setting-group" style={{flex: 2}}>
                    <label>Item Name</label>
                    <input type="text" value={newItem.name} onChange={e => setNewItem({...newItem, name: e.target.value})} placeholder="e.g. World Tour" required />
                </div>
                <div className="setting-group" style={{flex: 1}}>
                    <label>Amount</label>
                    <input type="number" value={newItem.amount} onChange={e => setNewItem({...newItem, amount: e.target.value})} placeholder="20000" required />
                </div>
                <div className="setting-group" style={{flex: 1}}>
                    <label>Start Year</label>
                    <input type="number" value={newItem.start_year} onChange={e => setNewItem({...newItem, start_year: e.target.value})} placeholder="2025" required />
                </div>
                <div className="setting-group" style={{flex: 1}}>
                    <label>End Year (Opt)</label>
                    <input type="number" value={newItem.end_year} onChange={e => setNewItem({...newItem, end_year: e.target.value})} placeholder="2030" />
                </div>
                <div className="setting-group" style={{flex: 1}}>
                    <label>Category</label>
                    <input type="text" list="disc-cat-list" value={newItem.category} onChange={e => setNewItem({...newItem, category: e.target.value})} />
                    <datalist id="disc-cat-list">{categories.map(c => <option key={c} value={c} />)}</datalist>
                </div>
                <div className="setting-group" style={{flex: 0.5, paddingBottom: '0.5rem'}}>
                    <label style={{display:'flex', alignItems:'center'}}>
                        <input type="checkbox" checked={newItem.is_recurring} onChange={e => setNewItem({...newItem, is_recurring: e.target.checked})} style={{width:'auto', marginRight:'5px'}} />
                        Recur?
                    </label>
                </div>
                <div className="setting-group" style={{display: 'flex', gap: '0.5rem'}}>
                     <button type="submit" style={{background: 'var(--gold-accent)', border: 'none', padding: '0.6rem', borderRadius: '4px', cursor: 'pointer', fontWeight:'bold', color: '#222'}}>
                         {newItem.item_id ? 'Save Changes' : 'Add'}
                     </button>
                     {newItem.item_id && (
                         <button type="button" onClick={() => setNewItem({ item_id: null, name: '', amount: '', start_year: new Date().getFullYear(), end_year: '', is_recurring: false, category: '', is_enabled: true })} style={{background: '#555', border: 'none', padding: '0.6rem', borderRadius: '4px', cursor: 'pointer', fontWeight:'bold', color: '#fff'}}>
                             Cancel
                         </button>
                     )}
                </div>
            </form>
            
            <table className="budget-table">
                <thead>
                    <tr>
                        <th>Enable</th>
                        <th>Name</th>
                        <th>Amount</th>
                        <th>Start</th>
                        <th>End</th>
                        <th>Recurring</th>
                        <th>Category</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {items.map(item => (
                        <tr 
                            key={item.item_id || Math.random()} 
                            style={{opacity: item.is_enabled !== 0 ? 1 : 0.4, cursor: 'pointer'}} 
                            onDoubleClick={() => handleRowDoubleClick(item)}
                            title="Double-click to edit"
                        >
                            <td onClick={(e) => e.stopPropagation()}>
                                <input 
                                    type="checkbox" 
                                    checked={!!item.is_enabled} 
                                    onChange={() => {
                                        if (!item.item_id) {
                                            alert("Cannot toggle: Item ID is missing.");
                                            return;
                                        }
                                        onUpdate({...item, is_enabled: !item.is_enabled});
                                    }}
                                    className="toggle-checkbox"
                                />
                            </td>
                            <td>{item.name}</td>
                            <td>{formatCurrency(item.amount)}</td>
                            <td>{item.start_year}</td>
                            <td>{item.end_year || (item.is_recurring ? 'Forever' : item.start_year)}</td>
                            <td>{item.is_recurring ? 'Yes' : 'No'}</td>
                            <td>{item.category || '-'}</td>
                            <td onClick={(e) => e.stopPropagation()}>
                                <button className="delete-btn" onClick={() => handleDelete(item.item_id)}>✕</button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </CollapsibleCard>
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
        <CollapsibleCard title="5) Principal Residence Strategy" className="grid-half-left">
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
        </CollapsibleCard>
    );
};

const PhaseConfiguration = ({ config, setConfig, onSave }) => {
    const [allCategories, setAllCategories] = useState([]);

    useEffect(() => {
        fetch('/api/filter-options')
            .then(r => r.json())
            .then(d => setAllCategories(d.categories || []));
    }, []);

    const getVal = (cat, phase) => {
        const val = config.phase_multipliers?.[cat]?.[phase];
        if (val !== undefined && val !== null) return val;
        if (phase === 'go') return 100;
        if (phase === 'slow') return 80;
        if (phase === 'no') return 20;
        return 100;
    }

    const updateMultiplier = (category, phase, value) => {
        const currentMultipliers = config.phase_multipliers || {};
        const catConfig = currentMultipliers[category] || { go: 100, slow: 80, no: 20 };
        const valToStore = value === '' ? '' : parseInt(value);
        const updated = {
            ...currentMultipliers,
            [category]: { ...catConfig, [phase]: valToStore }
        };
        setConfig(prev => ({ ...prev, phase_multipliers: updated }));
    };

    return (
        <CollapsibleCard title="7) Go / Slow / No-Go Phases" className="grid-half-left">
            <div style={{display:'flex', gap:'1rem'}}>
                <div className="setting-group" style={{flex:1}}>
                    <label>Retirement Age (Start Slow Go)</label>
                    <input type="number" name="retirement_age" value={config.retirement_age || ''} onChange={(e) => setConfig(p => ({...p, [e.target.name]: e.target.value}))} onBlur={onSave} />
                </div>
                <div className="setting-group" style={{flex:1}}>
                    <label>No Go Age (Low Energy)</label>
                    <input type="number" name="nogo_age" value={config.nogo_age || ''} onChange={(e) => setConfig(p => ({...p, [e.target.name]: e.target.value}))} onBlur={onSave} />
                </div>
            </div>
            
            <h4 style={{marginTop: '1rem', borderBottom: '1px solid #444'}}>Spending Intensity (%)</h4>
            <div style={{maxHeight: '150px', overflowY: 'auto'}}>
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
                                    <input type="number" style={{width: '100%'}} value={getVal(cat, 'go')} onChange={(e) => updateMultiplier(cat, 'go', e.target.value)} onBlur={onSave} />
                                </td>
                                <td style={{padding: '5px'}}>
                                    <input type="number" style={{width: '100%'}} value={getVal(cat, 'slow')} onChange={(e) => updateMultiplier(cat, 'slow', e.target.value)} onBlur={onSave} />
                                </td>
                                <td style={{padding: '5px'}}>
                                    <input type="number" style={{width: '100%'}} value={getVal(cat, 'no')} onChange={(e) => updateMultiplier(cat, 'no', e.target.value)} onBlur={onSave} />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </CollapsibleCard>
    );
};

const ForecastSettings = ({ config, setConfig, onSave, onSettingChange }) => {
    const handleChange = (e) => {
        const { name, value } = e.target;
        setConfig(prev => ({ ...prev, [name]: value }));
    };
    
    // Specialized handler for dropdowns to trigger immediate save/recalc
    const handleImmediateChange = (e) => {
        const { name, value } = e.target;
        if (onSettingChange) {
            onSettingChange(name, value);
        } else {
             // Fallback
             handleChange(e);
             // We assume onBlur will be called if user clicks away, but we want immediate effect.
        }
    }

    return (
        <CollapsibleCard title="Simulation Constants" className="grid-half-right">
            <div className="setting-group">
                <label>Withdrawal Strategy</label>
                <select 
                    name="withdrawal_strategy" 
                    value={config.withdrawal_strategy || 'standard'} 
                    onChange={handleImmediateChange} 
                    style={{background: '#444', color: '#fff'}}
                >
                    <option value="standard">Standard (Brokerage First)</option>
                    <option value="deferred_first">Legacy (IRA / Deferred First)</option>
                </select>
            </div>
            <div className="setting-group">
                <label>Tax Filing Status</label>
                <select 
                    name="tax_filing_status" 
                    value={config.tax_filing_status || 'single'} 
                    onChange={handleImmediateChange} 
                    style={{background: '#444', color: '#fff'}}
                >
                    <option value="single">Single</option>
                    <option value="joint">Married Filing Jointly</option>
                </select>
            </div>

            <div className="setting-group">
                <label>Roth Conversion Strategy</label>
                <select 
                    name="roth_conversion_target" 
                    value={config.roth_conversion_target || 'none'} 
                    onChange={handleImmediateChange} 
                    style={{background: '#444', color: '#fff'}}
                >
                    <option value="none">No Conversions</option>
                    <option value="fill_22">Fill to Top of 22% Bracket</option>
                </select>
            </div>
            
            <div className="setting-group">
                <label>Estimated State Tax Rate (e.g. 0.093 for 9.3%)</label>
                <input 
                    type="number" 
                    name="state_tax_rate" 
                    step="0.001" 
                    placeholder="0.05" 
                    value={config.state_tax_rate || ''} 
                    onChange={handleChange} 
                    onBlur={onSave} 
                />
                <small style={{color:'#999'}}>Applied to taxable income in simulation.</small>
            </div>
            
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
        </CollapsibleCard>
    );
};

const ForecastTelemetryTable = ({ simulationData }) => {
    if (!simulationData || simulationData.length === 0) return null;

    // --- FIX: Aggregate keys from ALL years to ensure future expenses (e.g. starting 2030) are included ---
    const allCategoriesSet = new Set();
    simulationData.forEach(row => {
        if (row.expense_breakdown) {
            Object.keys(row.expense_breakdown).forEach(key => allCategoriesSet.add(key));
        }
    });
    const categories = Array.from(allCategoriesSet).sort();

    return (
        <CollapsibleCard title="Detailed Flight Telemetry" className="grid-full" defaultOpen={false}>
            <div style={{overflowX: 'auto'}}>
                <table className="budget-table" style={{minWidth: '1000px'}}>
                    <thead>
                        <tr>
                            <th>Year</th>
                            <th>Age</th>
                            <th>Phase</th>
                            <th>Strategy</th>
                            <th>Liquid Assets</th>
                            <th>NW Delta</th>
                            <th>IRA Bal</th>
                            <th>Roth Bal</th>
                            <th>Taxable Bal</th>
                            <th style={{borderLeft: '2px solid #555', paddingLeft: '10px'}}>Taxable Income</th>
                            <th>Total Tax</th>
                            <th>Roth Conv.</th>
                            {categories.map(cat => (
                                <th key={cat}>{cat}</th>
                            ))}
                            <th>Total Expenses</th>
                        </tr>
                    </thead>
                    <tbody>
                        {simulationData.map(row => (
                            <tr key={row.year}>
                                <td>{row.year}</td>
                                <td>{row.age}</td>
                                <td>{row.phase}</td>
                                <td style={{color: row.strategy_executed === 'Accumulation' ? '#05c46b' : (row.strategy_executed.includes('Age < 60') ? '#ff9f43' : '#feca57')}}>
                                    {row.strategy_executed}
                                </td>
                                <td style={{fontWeight: 'bold'}}>{formatCurrency(row.liquid_assets)}</td>
                                <td style={{color: row.nw_delta >= 0 ? '#05c46b' : '#ff6b6b'}}>{formatCurrency(row.nw_delta)}</td>
                                <td style={{color: '#feca57'}}>{formatCurrency(row.bucket_deferred)}</td>
                                <td style={{color: '#ff9ff3'}}>{formatCurrency(row.bucket_roth)}</td>
                                <td style={{color: '#00f2fe'}}>{formatCurrency(row.bucket_taxable)}</td>
                                <td style={{borderLeft: '2px solid #555', paddingLeft: '10px'}}>{formatCurrency(row.tax_metrics?.taxable_income)}</td>
                                <td>{formatCurrency(row.tax_metrics?.total_tax)}</td>
                                <td style={{color: row.roth_conversion > 0 ? '#ff9ff3' : 'inherit'}}>{formatCurrency(row.roth_conversion)}</td>
                                
                                {categories.map(cat => (
                                    <td key={cat}>{formatCurrency(row.expense_breakdown[cat])}</td>
                                ))}
                                <td style={{fontWeight: 'bold', color: '#feca57'}}>{formatCurrency(row.total_expenses)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </CollapsibleCard>
    )
}

// --- MAIN VIEW ---

const ForecastView = () => {
    const { mode } = useMode();
    const [config, setConfig] = useState({});
    const [baseColCategories, setBaseColCategories] = useState([]);
    const [sunsetDates, setSunsetDates] = useState({}); 
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
            setSunsetDates(data.base_col_sunset_dates || {});
        });
        
        fetch('/api/forecast/discretionary').then(r => r.json()).then(setBudgetItems);
    }, []);

    // Recalculate Simulation
    useEffect(() => {
        fetch(`/api/forecast/simulation?mode=${mode}`).then(r => r.json()).then(data => {
            setSimulationData(data.simulation_series);
            setAlerts(data.alerts || []);
            if (data.settings && data.settings.starting_base_col) {
                setBaseColTotal(data.settings.starting_base_col);
            }
        });
    }, [refreshKey, config, mode]); 

    const saveConfig = async (configOverride = null) => {
        const configToSave = configOverride || config;
        await fetch('/api/forecast/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...configToSave,
                base_col_categories: baseColCategories,
                base_col_sunset_dates: sunsetDates
            })
        });
        // Only force refresh key update if we are NOT using an override (which implies we set state already)
        // Actually, always good to force re-fetch of sim data.
        setRefreshKey(k => k + 1);
    };
    
    // Wrapper for immediate updates
    const handleImmediateSettingChange = (name, value) => {
        const newConfig = { ...config, [name]: value };
        setConfig(newConfig);
        saveConfig(newConfig);
    }

    // Auto-save base categories or sunset dates change
    useEffect(() => {
        if (baseColCategories.length > 0) {
            saveConfig();
        }
    }, [baseColCategories, sunsetDates]);

    const handleLookbackChange = (years) => {
        setConfig(prev => ({ ...prev, base_col_lookback_years: years }));
        setTimeout(() => saveConfig({ ...config, base_col_lookback_years: years }), 100);
    };

    const handleSunsetChange = (cat, year) => {
        setSunsetDates(prev => ({
            ...prev,
            [cat]: year
        }));
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

    const handleUpdateItem = async (item) => {
        await fetch('/api/forecast/discretionary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item)
        });
        const res = await fetch('/api/forecast/discretionary');
        setBudgetItems(await res.json());
        setRefreshKey(k => k + 1);
    };

    return (
        <div className="forecast-view-container">
            {/* 1) The Runway (Full) */}
            <div className="chart-panel grid-full">
                <h2>1) The Runway (Age 95 Horizon)</h2>
                {alerts.length > 0 && (
                    <div style={{background: '#5a2a2a', color: '#ffc048', padding: '1rem', marginBottom: '1rem', borderRadius: '4px'}}>
                        <strong>Warning:</strong> {alerts.map((a, i) => <div key={i}>{a}</div>)}
                    </div>
                )}
                <RunwayChart data={simulationData} />
            </div>
            
            <div className="dashboard-grid">
                {/* 2) Expense Profile (Half Left) */}
                <div className="chart-panel grid-half-left">
                    <h3>2) Expense Profile</h3>
                    <ExpenseCompositionChart data={simulationData} />
                </div>

                {/* 3) Asset Composition (Half Right) */}
                <div className="chart-panel grid-half-right">
                    <h3>3) Asset Composition</h3>
                    <AssetCompositionChart data={simulationData} />
                </div>
            </div>

            {/* 4) Discretionary Budget (Full) */}
            <DiscretionaryBudget 
                items={budgetItems} 
                onAdd={handleAddItem} 
                onDelete={handleDeleteItem} 
                onUpdate={handleUpdateItem}
            />

            <div className="dashboard-grid">
                 {/* 5) Principal Residence (Half Left) */}
                <ResidenceSaleConfig
                    config={config}
                    setConfig={setConfig}
                    onSave={() => saveConfig()}
                />

                {/* 6) Base CoL Engine (Half Right) */}
                <BaseColCalculator 
                    selectedCategories={baseColCategories} 
                    onSelectionChange={setBaseColCategories} 
                    calculatedTotal={baseColTotal} 
                    lookbackYears={config.base_col_lookback_years}
                    onLookbackChange={handleLookbackChange}
                    sunsetDates={sunsetDates}
                    onSunsetChange={handleSunsetChange}
                />

                {/* 7) Go Slow No Go (Half Left) */}
                <PhaseConfiguration
                    config={config}
                    setConfig={setConfig}
                    onSave={() => saveConfig()}
                />

                {/* Spacer / Other Settings (Half Right) */}
                <ForecastSettings 
                    config={config} 
                    setConfig={setConfig} 
                    onSave={() => saveConfig()} 
                    onSettingChange={handleImmediateSettingChange}
                />
            </div>

            {/* Telemetry Tables below everything */}
            <ForecastTelemetryTable simulationData={simulationData} />
        </div>
    );
};

export default ForecastView;
