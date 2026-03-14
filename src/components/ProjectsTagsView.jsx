import { useState, useEffect, useMemo } from 'react';
import './ProjectsTagsView.css';

const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
}).format(value || 0);

const ProjectsTagsView = () => {
    const [tags, setTags] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [sizingMethod, setSizingMethod] = useState('count'); // 'count' or 'value'
    const [selectedTag, setSelectedTag] = useState(null);
    const [tagRecords, setTagRecords] = useState({ transactions: [], holdings: [] });
    const [recordsLoading, setRecordsLoading] = useState(false);

    useEffect(() => {
        const fetchTags = async () => {
            try {
                setIsLoading(true);
                const response = await fetch('/api/tags/summary');
                if (!response.ok) throw new Error('Failed to fetch tags');
                const data = await response.json();
                setTags(data);
            } catch (err) {
                console.error("Error fetching tags:", err);
            } finally {
                setIsLoading(false);
            }
        };
        fetchTags();
    }, []);

    const handleTagClick = async (tagName) => {
        setSelectedTag(tagName);
        setRecordsLoading(true);
        try {
            const response = await fetch(`/api/tags/${encodeURIComponent(tagName)}/records`);
            if (!response.ok) throw new Error('Failed to fetch records');
            const data = await response.json();
            setTagRecords(data);
        } catch (err) {
            console.error("Error fetching tag records:", err);
        } finally {
            setRecordsLoading(false);
        }
    };

    const closeDetails = () => {
        setSelectedTag(null);
        setTagRecords({ transactions: [], holdings: [] });
    };

    // Calculate min/max for tag cloud scaling
    const { minScale, maxScale } = useMemo(() => {
        if (tags.length === 0) return { minScale: 1, maxScale: 1 };
        const values = tags.map(t => sizingMethod === 'count' 
            ? t.tx_count + t.holding_count 
            : t.tx_value + t.holding_value
        );
        return {
            minScale: Math.min(...values),
            maxScale: Math.max(...values)
        };
    }, [tags, sizingMethod]);

    // Render individual Tag with dynamic sizing
    const renderTag = (tag) => {
        const metric = sizingMethod === 'count' 
            ? tag.tx_count + tag.holding_count 
            : tag.tx_value + tag.holding_value;
        
        // Scale between 0.9em and 3.5em based on relative size
        const range = maxScale - minScale || 1; // Prevent div by 0
        const scaleFactor = (metric - minScale) / range;
        const fontSize = 0.9 + (scaleFactor * 2.6);
        
        const totalValue = tag.tx_value + tag.holding_value;
        const totalCount = tag.tx_count + tag.holding_count;
        
        const titleText = `${tag.tag}\nItems: ${totalCount}\nTotal Vol: ${formatCurrency(totalValue)}`;

        return (
            <div 
                key={tag.tag} 
                className={`tag-item ${selectedTag === tag.tag ? 'selected' : ''}`}
                style={{ fontSize: `${fontSize}em` }}
                onClick={() => handleTagClick(tag.tag)}
                title={titleText}
            >
                {tag.tag}
            </div>
        );
    };

    const activeTagSummary = tags.find(t => t.tag === selectedTag);

    return (
        <div className="tags-view-container">
            <div className="tag-cloud-card">
                <div className="tag-cloud-header">
                    <h2>Project & Tag Inspector</h2>
                    <div className="tag-controls">
                        <label style={{marginRight: '0.5rem', color: '#ccc'}}>Size by:</label>
                        <select value={sizingMethod} onChange={(e) => setSizingMethod(e.target.value)}>
                            <option value="count">Number of Items</option>
                            <option value="value">Total Volume ($)</option>
                        </select>
                    </div>
                </div>
                
                <div className="tag-cloud-area">
                    {isLoading ? <p>Scanning core memory for tags...</p> : 
                     tags.length === 0 ? <p>No tags found in the system. Edit transactions or assets to add them.</p> :
                     tags.map(renderTag)}
                </div>
            </div>

            {selectedTag && (
                <div className="tag-detail-card">
                    <h3>
                        Records for tag: #{selectedTag}
                        <button className="close-btn" onClick={closeDetails}>✕</button>
                    </h3>
                    
                    {activeTagSummary && (
                        <div className="tag-summary-stats">
                            <div className="stat-box">
                                <label>Transactions</label>
                                <span>{activeTagSummary.tx_count} ({formatCurrency(activeTagSummary.tx_value)})</span>
                            </div>
                            <div className="stat-box">
                                <label>Holdings</label>
                                <span>{activeTagSummary.holding_count} ({formatCurrency(activeTagSummary.holding_value)})</span>
                            </div>
                        </div>
                    )}

                    {recordsLoading ? <p>Loading detailed records...</p> : (
                        <div className="tag-tables-grid">
                            {tagRecords.transactions.length > 0 && (
                                <div className="tag-table-wrapper">
                                    <h4>Transactions</h4>
                                    <table className="tag-table">
                                        <thead>
                                            <tr>
                                                <th>Date</th>
                                                <th>Description</th>
                                                <th>Account</th>
                                                <th className="numeric">Amount</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {tagRecords.transactions.map(tx => (
                                                <tr key={tx.transaction_id}>
                                                    <td>{tx.transaction_date.split(' ')[0]}</td>
                                                    <td title={tx.description}>
                                                        {tx.description.length > 30 ? tx.description.substring(0,30) + '...' : tx.description}
                                                    </td>
                                                    <td>{tx.account_id}</td>
                                                    <td className="numeric">{formatCurrency(tx.amount)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                            
                            {tagRecords.holdings.length > 0 && (
                                <div className="tag-table-wrapper">
                                    <h4>Holdings / Assets</h4>
                                    <table className="tag-table">
                                        <thead>
                                            <tr>
                                                <th>Symbol/Name</th>
                                                <th>Account</th>
                                                <th>Qty</th>
                                                <th className="numeric">Value</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {tagRecords.holdings.map(h => (
                                                <tr key={h.holding_id}>
                                                    <td>{h.symbol}</td>
                                                    <td>{h.account_id}</td>
                                                    <td>{h.quantity.toFixed(2)}</td>
                                                    <td className="numeric">{formatCurrency(h.market_value)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            {tagRecords.transactions.length === 0 && tagRecords.holdings.length === 0 && (
                                <p>No records found. The tag might have been removed.</p>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default ProjectsTagsView;
