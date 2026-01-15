import { ResponsivePie } from '@nivo/pie';

const PieChart = ({ data }) => {
    // Helper to format currency for tooltips
    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);

    // Helper to format percentage for labels
    const formatPercentage = (value) => `${value.toFixed(1)}%`;

    return (
        <div style={{ height: '350px' }}>
            <ResponsivePie
                data={data}
                margin={{ top: 40, right: 80, bottom: 80, left: 80 }}
                innerRadius={0.5}
                padAngle={0.7}
                cornerRadius={3}
                activeOuterRadiusOffset={8}
                borderWidth={1}
                borderColor={{ from: 'color', modifiers: [['darker', 0.2]] }}
                arcLinkLabelsSkipAngle={10}
                arcLinkLabelsTextColor="#ccc"
                arcLinkLabelsThickness={2}
                arcLinkLabelsColor={{ from: 'color' }}
                arcLabelsSkipAngle={10}
                arcLabelsTextColor={{ from: 'color', modifiers: [['darker', 2]] }}
                // Use the percentage from the backend for the label
                arcLabel={d => formatPercentage(d.data.percentage)}
                defs={[
                    // ... (can add patterns/gradients if desired, skipping for now)
                ]}
                legends={[
                    {
                        anchor: 'bottom',
                        direction: 'row',
                        justify: false,
                        translateX: 0,
                        translateY: 56,
                        itemsSpacing: 0,
                        itemWidth: 100,
                        itemHeight: 18,
                        itemTextColor: '#999',
                        itemDirection: 'left-to-right',
                        itemOpacity: 1,
                        symbolSize: 18,
                        symbolShape: 'circle',
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
                tooltip={({ datum: { id, value, color } }) => (
                    <div
                        style={{
                            padding: '12px',
                            background: 'var(--dark-bg)',
                            color: 'var(--text-color)',
                            border: `1px solid var(--border-color)`,
                        }}
                    >
                        <strong style={{ color }}>{id}</strong>
                        <br />
                        Value: {formatCurrency(value)}
                    </div>
                )}
                theme={{
                    tooltip: {
                        container: {
                            background: 'var(--dark-bg)',
                        },
                    },
                    labels: {
                        text: {
                            fill: '#fff',
                            fontSize: 14,
                        },
                    },
                    legends: {
                        text: {
                            fill: '#bbb'
                        }
                    }
                }}
            />
        </div>
    );
};

export default PieChart;
