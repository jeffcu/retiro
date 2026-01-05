import { ResponsiveSankey } from '@nivo/sankey';

const SankeyChart = ({ data }) => {

    // Helper to format numbers with commas and two decimal places.
    const formatValue = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(value);

    return (
        <div style={{ height: '600px', width: '100%' }}>
            <ResponsiveSankey
                data={data} 
                margin={{ top: 40, right: 160, bottom: 40, left: 50 }}
                align="justify"
                colors={{ scheme: 'category10' }}
                nodeOpacity={1}
                nodeHoverOthersOpacity={0.35}
                nodeThickness={18}
                nodeSpacing={24}
                nodeBorderWidth={0}
                nodeBorderColor={{ from: 'color', modifiers: [['darker', 0.8]] }}
                nodeBorderRadius={3}
                linkOpacity={0.5}
                linkHoverOthersOpacity={0.1}
                linkContract={3}
                enableLinkGradient={true}
                labelPosition="outside"
                labelOrientation="vertical"
                labelPadding={16}
                labelTextColor={{ from: 'color', modifiers: [['darker', 1]] }}
                
                // --- DIAGNOSTIC ENHANCEMENT --- //
                // This new property adds a tooltip that displays the value when hovering over a link.
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

                legends={[
                    {
                        anchor: 'bottom-right',
                        direction: 'column',
                        translateX: 130,
                        itemWidth: 100,
                        itemHeight: 14,
                        itemDirection: 'right-to-left',
                        itemsSpacing: 2,
                        itemTextColor: '#999',
                        symbolSize: 14,
                        effects: [
                            {
                                on: 'hover',
                                style: {
                                    itemTextColor: '#fff'
                                }
                            }
                        ]
                    }
                ]}
            />
        </div>
    )
};

export default SankeyChart;
