import { useState, useEffect } from 'react';
import './IncomeSankeySettings.css';

const IncomeSankeySettings = ({ onSettingsChanged }) => {
    const [allCategories, setAllCategories] = useState([]);
    const [selectedCategories, setSelectedCategories] = useState(new Set());
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        const fetchSettings = async () => {
            try {
                setIsLoading(true);
                const [categoriesRes, savedSettingsRes] = await Promise.all([
                    fetch('/api/filter-options/income-categories'),
                    fetch('/api/settings/sankey-income-categories')
                ]);

                if (!categoriesRes.ok || !savedSettingsRes.ok) {
                    throw new Error("Failed to fetch income category settings");
                }

                const categoriesData = await categoriesRes.json();
                const savedSettingsData = await savedSettingsRes.json();

                setAllCategories(categoriesData);
                setSelectedCategories(new Set(savedSettingsData));
            } catch (error) {
                console.error("Failed to load income Sankey settings:", error);
            } finally {
                setIsLoading(false);
            }
        };
        fetchSettings();
    }, []);

    const handleToggle = (category) => {
        setSelectedCategories(prev => {
            const newSet = new Set(prev);
            if (newSet.has(category)) {
                newSet.delete(category);
            } else {
                newSet.add(category);
            }
            return newSet;
        });
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const response = await fetch('/api/settings/sankey-income-categories', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(Array.from(selectedCategories)),
            });
            if (!response.ok) throw new Error('Failed to save settings');
            alert('Income source settings saved successfully!');
            onSettingsChanged(); // Notify parent to refresh other components if needed
        } catch (error) {
            console.error("Failed to save settings:", error);
            alert(`Error: ${error.message}`);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className='income-settings-card'>
            <h3>Income Sources Sankey Settings</h3>
            <p>Select the income categories to display in the "Income Sources" chart on the Home screen. 'Drawdown' is always included by default.</p>
            {isLoading ? (
                <p>Loading categories...</p>
            ) : (
                <>
                    <div className='category-list'>
                        {allCategories.map(cat => (
                            <div key={cat} className='category-item'>
                                <input 
                                    type="checkbox" 
                                    id={`income-cat-${cat}`}
                                    checked={selectedCategories.has(cat)}
                                    onChange={() => handleToggle(cat)}
                                />
                                <label htmlFor={`income-cat-${cat}`}>{cat}</label>
                            </div>
                        ))}
                    </div>
                    <div className='settings-actions'>
                        <button onClick={handleSave} disabled={isSaving}>
                            {isSaving ? 'Saving...' : 'Save Settings'}
                        </button>
                    </div>
                </>
            )}
        </div>
    );
};

export default IncomeSankeySettings;