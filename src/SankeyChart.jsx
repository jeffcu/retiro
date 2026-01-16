import { ResponsiveSankey } from '@nivo/sankey';

const SankeyChart = ({ data, onNodeClick = () => {} }) => {

    // Helper to format numbers with commas and two decimal places.
    const formatValue = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);

    const handleNodeClick = (node, event) => {
        // Pass the entire node object up to the parent handler.
        onNodeClick(node);
    };

    return (
        // --- FIX: Removed inconsistent light-background wrapper div that was causing a rendering crash. --- //
        <div style={{ height: '600px', width: '100%' }}>
            <ResponsiveSankey
                data={data} 
                margin={{ top: 40, right: 200, bottom: 40, left: 80 }}
                align="center"
                colors={{ scheme: 'category10' }}
                nodeOpacity={1}
                nodeHoverOthersOpacity={0.35}
                nodeThickness={24}
                nodeSpacing={8}
                nodeBorderWidth={0}
                nodeBorderRadius={3}
                
                // Link/flow styling for DARK background
                linkOpacity={0.6}
                linkHoverOthersOpacity={0.1}
                linkContract={0}
                enableLinkGradient={true}

                labelPosition="outside"
                labelOrientation="horizontal"
                labelPadding={16}
                // --- FIX: Explicitly set a single, high-contrast color for all labels. ---
                labelTextColor="#f0f0f0"
                
                onClick={handleNodeClick}
                
                // Tooltip for links (flows) with dark theme
                linkTooltip={({ link }) => (
                    <div style={{
                        padding: '12px',
                        background: '#222',
                        color: '#eee',
                        border: '1px solid #333',
                        borderRadius: '3px',
                    }}>
                        <strong>{link.source.id}</strong> → <strong>{link.target.id}</strong>
                        <br />
                        {formatValue(link.value)}
                    </div>
                )}

                // Tooltip for nodes with dark theme
                nodeTooltip={node => (
                    <div style={{
                        padding: '12px',
                        background: '#222',
                        color: '#eee',
                        border: '1px solid #333',
                        borderRadius: '3px',
                    }}>
                        <strong>{node.id}</strong>
                        <br />
                        {formatValue(node.value)}
                    </div>
                )}
                
                // Theme for other elements like tooltips and axes (if any).
                // Label color is now handled by the `labelTextColor` prop for direct control.
                theme={{
                    labels: {
                        text: {
                            // `fill` is now controlled by the `labelTextColor` prop above.
                            fontSize: 12
                        }
                    },
                    tooltip: {
                        container: {
                            background: '#222',
                            color: '#eee',
                            border: '1px solid #333'
                        }
                    }
                }}
            />
        </div>
    )
};

export default SankeyChart;
