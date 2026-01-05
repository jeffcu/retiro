import SankeyChart from '../SankeyChart';

const mockReturnData = {
    nodes: [
        { id: 'Gross Return' },
        { id: 'Net Return' },
        { id: 'Fees' },
        { id: 'Taxes' },
    ],
    links: [
        { source: 'Gross Return', target: 'Fees', value: 1500 },
        { source: 'Gross Return', target: 'Taxes', value: 3500 },
        { source: 'Gross Return', target: 'Net Return', value: 25000 },
    ],
};

const MockSankey = ({ type }) => {
    // In the future, this could select different mock data based on 'type'
    const data = mockReturnData;

    return (
        <div style={{ position: 'relative' }}>
            <div style={{ 
                position: 'absolute',
                top: 0, left: 0, right: 0, bottom: 0, 
                background: 'rgba(47, 47, 47, 0.7)',
                color: 'white',
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                zIndex: 10,
                borderRadius: '8px',
                fontSize: '1.2em',
                fontWeight: 'bold'
            }}>
                [Mock Data - Implementation Pending]
            </div>
            <div style={{ opacity: 0.2 }}>
                <SankeyChart data={data} />
            </div>
        </div>
    );
};

export default MockSankey;
