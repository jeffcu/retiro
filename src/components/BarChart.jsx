import { ResponsiveBar } from '@nivo/bar';

const BarChart = ({ data, indexBy, keys, axisLeftLabel, axisBottomLabel }) => {

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);

    return (
        <div style={{ height: '350px' }}>
            <ResponsiveBar
                data={data}
                keys={keys}
                indexBy={indexBy}
                margin={{ top: 20, right: 30, bottom: 60, left: 100 }}
                padding={0.3}
                valueScale={{ type: 'linear' }}
                indexScale={{ type: 'band', round: true }}
                colors={{ scheme: 'nivo' }}
                borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
                axisTop={null}
                axisRight={null}
                axisBottom={{
                    tickSize: 5,
                    tickPadding: 5,
                    tickRotation: 0,
                    legend: axisBottomLabel,
                    legendPosition: 'middle',
                    legendOffset: 32,
                }}
                axisLeft={{
                    tickSize: 5,
                    tickPadding: 5,
                    tickRotation: 0,
                    legend: axisLeftLabel,
                    legendPosition: 'middle',
                    legendOffset: -80,
                    format: formatCurrency
                }}
                labelSkipWidth={12}
                labelSkipHeight={12}
                labelTextColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
                legends={[]}
                animate={true}
                motionStiffness={90}
                motionDamping={15}
                tooltip={({ id, value, indexValue }) => (
                    <div style={{
                        padding: '12px',
                        background: '#222',
                        color: '#fff',
                        border: '1px solid #333',
                        borderRadius: '3px',
                    }}>
                        <strong>{indexValue}</strong><br />
                        {id}: {formatCurrency(value)}
                    </div>
                )}
                theme={{
                    axis: {
                        ticks: { text: { fill: '#bbb' } },
                        legend: { text: { fill: '#bbb' } },
                    },
                    grid: {
                        line: { stroke: '#444' }
                    },
                    tooltip: {
                        container: {
                            background: 'var(--dark-bg)',
                            color: 'var(--text-color)',
                            border: `1px solid var(--border-color)`
                        }
                    }
                }}
            />
        </div>
    );
};

export default BarChart;
