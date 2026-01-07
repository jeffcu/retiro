import { ResponsiveSankey } from '@nivo/sankey';

const SankeyChart = ({ data }) => {

    // Helper to format numbers with commas and two decimal places.
    const formatValue = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(value);

    const handleNodeClick = (node, event) => {
        // Placeholder for drill-down functionality (PRS 2.2)
        const details = `Node Clicked:\nID: ${node.id}\nValue: ${formatValue(node.value)}`;
        console.log(details);
        alert(details);
    };

    return (
        // --- VISUAL REFINEMENT (User Request) --- //
        // Added a light grey background to the chart container for better contrast.
        <div style={{ height: '600px', width: '100%', backgroundColor: '#f5f5f5', borderRadius: '4px', padding: '1rem' }}>
            <ResponsiveSankey
                data={data} 
                margin={{ top: 20, right: 160, bottom: 20, left: 50 }}
                align="justify"
                colors={{ scheme: 'category10' }} // A colorblind-safe, distinct palette
                nodeOpacity={1}
                nodeHoverOthersOpacity={0.35}
                nodeThickness={18}
                nodeSpacing={24}
                nodeBorderWidth={0}
                nodeBorderColor={{ from: 'color', modifiers: [['darker', 0.8]] }}
                nodeBorderRadius={3}
                
                // Link/flow styling for light background
                linkOpacity={0.6}
                linkColor="#adadad" // Medium grey for good contrast on light bg
                enableLinkGradient={false}

                linkHoverOthersOpacity={0.1}
                linkContract={3}
                labelPosition="outside"
                labelOrientation="horizontal"
                labelPadding={16}
                // Label color inverted for light background
                labelTextColor="#333333"

                onClick={handleNodeClick} // Added click handler for future drill-down
                
                // Tooltip for links (flows)
                linkTooltip={({ link }) => (
                    <div style={{
                        padding: '12px',
                        background: '#fff',
                        color: '#000',
                        border: '1px solid #ccc',
                        borderRadius: '3px',
                    }}>
                        <strong>{link.source.id}</strong> → <strong>{link.target.id}</strong>
                        <br />
                        {formatValue(link.value)}
                    </div>
                )}

                // Tooltip for nodes (bars) - Hardened to prevent crashes on bad data.
                nodeTooltip={node => (
                    <div style={{
                        padding: '12px',
                        background: '#fff',
                        color: '#000',
                        border: '1px solid #ccc',
                        borderRadius: '3px',
                    }}>
                        <strong>{node.id}</strong>
                        <br />
                        {/* Defensive check: Ensure node.value is a number before formatting. */}
                        {typeof node.value === 'number' ? formatValue(node.value) : 'N/A'}
                    </div>
                )}
                
                // legends prop removed to simplify the UI as per prior request.
            />
        </div>
    )
};

export default SankeyChart;
