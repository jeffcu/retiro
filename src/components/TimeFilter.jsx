import './TimeFilter.css';

const TimeFilter = ({ selectedPeriod, onPeriodChange }) => {
    const periods = [
        { id: 'all', label: 'All Time' },
        { id: '2025', label: '2025' },
        { id: '2024', label: '2024' },
        { id: '6m', label: 'Last 6 Months' },
        { id: '3m', label: 'Last 3 Months' },
        { id: '1m', label: 'Last 1 Month' },
    ];

    return (
        <div className="time-filter-container">
            {periods.map(p => (
                <button
                    key={p.id}
                    className={`time-filter-btn ${selectedPeriod === p.id ? 'active' : ''}`}
                    onClick={() => onPeriodChange(p.id)}
                >
                    {p.label}
                </button>
            ))}
        </div>
    );
};

export default TimeFilter;