import { ResponsiveSankey } from '@nivo/sankey';

const SankeyChart = ({ data }) => {

    // Helper to format numbers with commas and two decimal places.
    const formatValue = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
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
                // --- LAYOUT OPTIMIZATION (User Request) ---
                // Tighter margins, more compact layout, and thicker nodes/flows.
                margin={{ top: 40, right: 200, bottom: 40, left: 80 }}
                align="center" // 'center' provides a more compact layout than 'justify'
                colors={{ scheme: 'category10' }} // A colorblind-safe, distinct palette
                nodeOpacity={1}
                nodeHoverOthersOpacity={0.35}
                nodeThickness={24} // Increased for more visual weight
                nodeSpacing={8}    // Decreased for tighter vertical layout
                nodeBorderWidth={0}
                nodeBorderRadius={3}
                
                // Link/flow styling for light background
                linkOpacity={0.6}
                linkColor="#adadad" // Medium grey for good contrast on light bg
                enableLinkGradient={false}

                linkHoverOthersOpacity={0.1}
                linkContract={0} // Removed contract for thicker-appearing flows
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

                // --- FIX: Display node name and value on hover --- //
                // Reverted to a simpler implementation to ensure both the node's ID (name)
                // and its value are always displayed as requested.
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
                        {formatValue(node.value)}
                    </div>
                )}
                
                // legends prop removed to simplify the UI as per prior request.
            />
        </div>
    )
};

export default SankeyChart;
