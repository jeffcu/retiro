import { useState, useEffect } from 'react';
import './TaxFactsEditor.css';

const TaxFactsEditor = () => {
    const currentYear = new Date().getFullYear();
    const [selectedYear, setSelectedYear] = useState(currentYear - 1);
    const [statusMessage, setStatusMessage] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const initialFormState = {
        filing_status: 'single',
        fed_taxable_income: '',
        fed_total_tax: '',
        state_taxable_income: '',
        state_total_tax: '',
    };
    const [formData, setFormData] = useState(initialFormState);

    useEffect(() => {
        const fetchTaxFacts = async () => {
            setIsLoading(true);
            setStatusMessage(`Loading data for ${selectedYear}...`);
            try {
                const response = await fetch(`/api/tax-facts/${selectedYear}`);
                if (response.ok) {
                    const data = await response.json();
                    // Populate form with fetched data, handling nulls
                    setFormData({
                        filing_status: data.filing_status || 'single',
                        fed_taxable_income: data.fed_taxable_income || '',
                        fed_total_tax: data.fed_total_tax || '',
                        state_taxable_income: data.state_taxable_income || '',
                        state_total_tax: data.state_total_tax || '',
                    });
                    setStatusMessage(`Loaded existing data for ${selectedYear}.`);
                } else if (response.status === 404) {
                    setFormData(initialFormState); // Reset form if no data exists
                    setStatusMessage(`No data found for ${selectedYear}. Enter new facts.`);
                } else {
                    throw new Error(`Failed to fetch data: ${response.statusText}`);
                }
            } catch (error) {
                console.error('Fetch error:', error);
                setStatusMessage(`Error loading data: ${error.message}`);
                setFormData(initialFormState);
            } finally {
                setIsLoading(false);
            }
        };

        fetchTaxFacts();
    }, [selectedYear]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSave = async (e) => {
        e.preventDefault();
        setIsSaving(true);
        setStatusMessage('Saving...');

        // Convert empty strings to null and numbers to floats for the backend
        const payload = Object.fromEntries(
            Object.entries(formData).map(([key, value]) => {
                if (key === 'filing_status') {
                    return [key, value];
                }
                const num = parseFloat(value);
                return [key, isNaN(num) ? null : num];
            })
        );

        try {
            const response = await fetch(`/api/tax-facts/${selectedYear}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to save data');
            }

            const result = await response.json();
            console.log('Save successful:', result);
            setStatusMessage(`Data for ${selectedYear} saved successfully.`);
        } catch (error) {
            console.error('Save error:', error);
            setStatusMessage(`Error saving data: ${error.message}`);
        } finally {
            setIsSaving(false);
        }
    };

    const yearOptions = Array.from({ length: 10 }, (_, i) => currentYear - 1 - i);

    const taxFields = [
        { id: 'fed_taxable_income', label: 'Federal Taxable Income', form: 'Form 1040, Line 15' },
        { id: 'fed_total_tax', label: 'Federal Total Tax', form: 'Form 1040, Line 24' },
        { id: 'state_taxable_income', label: 'State Taxable Income', form: 'CA 540, Line 19' },
        { id: 'state_total_tax', label: 'State Total Tax', form: 'CA 540, Line 31' },
    ];

    return (
        <div className="tax-editor-container">
            <h3>Tax Facts for After-Tax Calculations</h3>
            <p>Enter the following values from your filed tax returns. This data is stored locally and used to calculate the 'After-Tax' portion of the portfolio return waterfall.</p>
            
            <form onSubmit={handleSave}>
                <div className="tax-form-header">
                    <div className="form-group-inline">
                        <label htmlFor="tax_year">Tax Year</label>
                        <select id="tax_year" name="tax_year" value={selectedYear} onChange={(e) => setSelectedYear(parseInt(e.target.value))}>
                            {yearOptions.map(year => <option key={year} value={year}>{year}</option>)}
                        </select>
                    </div>
                    <div className="form-group-inline">
                        <label htmlFor="filing_status">Filing Status</label>
                        <select id="filing_status" name="filing_status" value={formData.filing_status} onChange={handleInputChange}>
                            <option value="single">Single</option>
                            <option value="married_filing_jointly">Married Filing Jointly</option>
                            <option value="married_filing_separately">Married Filing Separately</option>
                            <option value="head_of_household">Head of Household</option>
                        </select>
                    </div>
                </div>

                <div className="tax-fields-grid">
                    {taxFields.map(field => (
                        <div className="tax-field-item" key={field.id}>
                            <label htmlFor={field.id}>{field.label}</label>
                            <span className="form-location">{field.form}</span>
                            <div className="currency-input">
                                <span>$</span>
                                <input 
                                    type="number" 
                                    id={field.id} 
                                    name={field.id}
                                    value={formData[field.id]}
                                    onChange={handleInputChange}
                                    placeholder="0"
                                    step="0.01"
                                    disabled={isLoading}
                                />
                            </div>
                        </div>
                    ))}
                </div>

                <div className="tax-form-actions">
                    {statusMessage && <div className="status-message">{statusMessage}</div>}
                    <button type="submit" disabled={isSaving || isLoading}>
                        {isSaving ? 'Saving...' : `Save ${selectedYear} Facts`}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default TaxFactsEditor;
