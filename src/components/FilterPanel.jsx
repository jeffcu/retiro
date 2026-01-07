import { useState, useEffect } from 'react';
import './FilterPanel.css';

const FilterPanel = ({ config, onFilterSubmit }) => {
    const [filterState, setFilterState] = useState({});
    const [options, setOptions] = useState({});

    useEffect(() => {
        // Initialize filter state from config
        const initialState = config.reduce((acc, item) => {
            acc[item.id] = '';
            return acc;
        }, {});
        setFilterState(initialState);

        // Fetch options for select dropdowns
        const fetchOptions = async () => {
            try {
                const response = await fetch('/api/filter-options');
                if (!response.ok) throw new Error('Failed to fetch filter options');
                const data = await response.json();
                setOptions(data);
            } catch (error) {
                console.error(error);
            }
        };
        fetchOptions();
    }, [config]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFilterState(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        // Remove empty filters before submitting
        const activeFilters = Object.fromEntries(
            Object.entries(filterState).filter(([_, value]) => value !== '' && value !== 'All')
        );
        onFilterSubmit(activeFilters);
    };

    return (
        <form onSubmit={handleSubmit} className="filter-panel">
            <div className="filter-grid">
                {config.map(item => (
                    <div key={item.id} className="filter-item">
                        <label htmlFor={item.id}>{item.label}</label>
                        {item.type === 'select' ? (
                            <select id={item.id} name={item.id} value={filterState[item.id] || ''} onChange={handleChange}>
                                <option value="">All</option>
                                {(options[item.optionsKey] || []).map(opt => (
                                    <option key={opt} value={opt}>{opt}</option>
                                ))}
                            </select>
                        ) : (
                            <input
                                type="text"
                                id={item.id}
                                name={item.id}
                                placeholder={item.placeholder}
                                value={filterState[item.id] || ''}
                                onChange={handleChange}
                            />
                        )}
                    </div>
                ))}
            </div>
            <div className="filter-actions">
                <button type="submit">Apply Filters</button>
            </div>
        </form>
    );
};

export default FilterPanel;
