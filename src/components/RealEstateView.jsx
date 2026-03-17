import { useState, useEffect } from 'react';
import './RealEstateView.css';
import { useMode } from '../context/ModeContext';

const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
}).format(value || 0);

const PropertyCard = ({ property, onEdit, onDelete }) => (
    <div className={`property-card ${property.is_primary ? 'primary' : ''}`}>
        <div className="property-header">
            <h3>
                {property.name} 
                {property.is_primary && <span className="primary-badge">Primary</span>}
            </h3>
            <div className="card-actions">
                <button className="action-btn" onClick={() => onEdit(property)} title="Edit">✎</button>
                <button className="action-btn delete-btn" onClick={() => onDelete(property.property_id)} title="Delete">🗑️</button>
            </div>
        </div>
        <div className="property-details">
            <div className="detail-item">
                <label>Current Value</label>
                <span>{formatCurrency(property.current_value)}</span>
            </div>
            <div className="detail-item">
                <label>Mortgage Balance</label>
                <span>{formatCurrency(property.mortgage_balance)}</span>
            </div>
            <div className="detail-item">
                <label>Purchase Price</label>
                <span>{formatCurrency(property.purchase_price)}</span>
            </div>
            <div className="detail-item">
                <label>Appreciation Rate</label>
                <span>{(property.appreciation_rate * 100).toFixed(2)}%</span>
            </div>
            {property.purchase_year && (
                <div className="detail-item">
                    <label>Future Purchase Year</label>
                    <span style={{color: 'var(--gold-accent)'}}>{property.purchase_year}</span>
                </div>
            )}
            {property.sale_year && (
                <div className="detail-item">
                    <label>Liquidation Year</label>
                    <span style={{color: 'var(--gold-accent)'}}>{property.sale_year}</span>
                </div>
            )}
            {property.fixed_sale_price !== null && property.fixed_sale_price !== undefined && (
                <div className="detail-item">
                    <label>Predetermined Sale Price</label>
                    <span style={{color: 'var(--gold-accent)'}}>{formatCurrency(property.fixed_sale_price)}</span>
                </div>
            )}
            {property.annual_maintenance > 0 && (
                <div className="detail-item">
                    <label>Annual Maint. Drag</label>
                    <span style={{color: '#ff6b6b'}}>{formatCurrency(property.annual_maintenance)}/yr</span>
                </div>
            )}
            <div className="equity-highlight">
                <label>Equity</label>
                <span>{formatCurrency(property.current_value - property.mortgage_balance)}</span>
            </div>
        </div>
    </div>
);

const RealEstateView = () => {
    const { mode } = useMode();
    const [properties, setProperties] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState(null);

    const initialForm = {
        name: '',
        purchase_price: '',
        mortgage_balance: '',
        current_value: '',
        appreciation_rate: 0.03,
        is_primary: false,
        purchase_year: '',
        sale_year: '',
        annual_maintenance: 0,
        fixed_sale_price: ''
    };
    const [formData, setFormData] = useState(initialForm);

    const fetchProperties = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`/api/properties?mode=${mode}`);
            if (!response.ok) throw new Error('Failed to fetch properties');
            const data = await response.json();
            setProperties(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchProperties();
    }, [mode]);

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const payload = {
            ...formData,
            purchase_price: parseFloat(formData.purchase_price),
            mortgage_balance: parseFloat(formData.mortgage_balance),
            current_value: parseFloat(formData.current_value),
            appreciation_rate: parseFloat(formData.appreciation_rate),
            purchase_year: formData.purchase_year ? parseInt(formData.purchase_year) : null,
            sale_year: formData.sale_year ? parseInt(formData.sale_year) : null,
            annual_maintenance: parseFloat(formData.annual_maintenance || 0),
            fixed_sale_price: formData.fixed_sale_price !== '' && formData.fixed_sale_price !== null ? parseFloat(formData.fixed_sale_price) : null
        };

        try {
            let response;
            if (editingId) {
                response = await fetch(`/api/properties/${editingId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                response = await fetch('/api/properties', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            }

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Operation failed');
            }

            setShowForm(false);
            setEditingId(null);
            setFormData(initialForm);
            fetchProperties();
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    const handleEdit = (prop) => {
        setFormData({
            name: prop.name,
            purchase_price: prop.purchase_price,
            mortgage_balance: prop.mortgage_balance,
            current_value: prop.current_value,
            appreciation_rate: prop.appreciation_rate,
            is_primary: prop.is_primary,
            purchase_year: prop.purchase_year || '',
            sale_year: prop.sale_year || '',
            annual_maintenance: prop.annual_maintenance || 0,
            fixed_sale_price: prop.fixed_sale_price !== null && prop.fixed_sale_price !== undefined ? prop.fixed_sale_price : ''
        });
        setEditingId(prop.property_id);
        setShowForm(true);
    };

    const handleDelete = async (id) => {
        if (!confirm('Delete this property?')) return;
        try {
            const response = await fetch(`/api/properties/${id}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Failed to delete');
            fetchProperties();
        } catch (err) {
            alert(err.message);
        }
    };

    const startNewProperty = () => {
        if (properties.length >= 12) {
            alert("Maximum property limit reached.");
            return;
        }
        setFormData(initialForm);
        setEditingId(null);
        setShowForm(true);
    };

    return (
        <div className="real-estate-view-container">
            {showForm && (
                <div className="property-form-card">
                    <h3>{editingId ? 'Edit Property' : 'Add Property'}</h3>
                    <form onSubmit={handleSubmit} className="property-form">
                        <div className="form-group">
                            <label>Property Name</label>
                            <input type="text" name="name" value={formData.name} onChange={handleInputChange} placeholder="e.g. Principal Residence" required />
                        </div>
                         <div className="form-group">
                            <label>Purchase Price</label>
                            <input type="number" name="purchase_price" value={formData.purchase_price} onChange={handleInputChange} step="0.01" required />
                        </div>
                        <div className="form-group">
                            <label>Current Value Estimate</label>
                            <input type="number" name="current_value" value={formData.current_value} onChange={handleInputChange} step="0.01" required />
                        </div>
                        <div className="form-group">
                            <label>Mortgage Balance</label>
                            <input type="number" name="mortgage_balance" value={formData.mortgage_balance} onChange={handleInputChange} step="0.01" required />
                        </div>
                         <div className="form-group">
                            <label>Annual Appreciation Rate (e.g. 0.03 = 3%)</label>
                            <input type="number" name="appreciation_rate" value={formData.appreciation_rate} onChange={handleInputChange} step="0.001" required />
                        </div>
                        
                        <div className="form-group">
                            <label>Target Purchase Year (Optional)</label>
                            <input type="number" name="purchase_year" value={formData.purchase_year} onChange={handleInputChange} placeholder="e.g. 2028" />
                        </div>
                        <div className="form-group">
                            <label>Target Sale Year (Optional)</label>
                            <input type="number" name="sale_year" value={formData.sale_year} onChange={handleInputChange} placeholder="e.g. 2040" />
                        </div>
                        <div className="form-group">
                            <label>Annual Maintenance ($)</label>
                            <input type="number" name="annual_maintenance" value={formData.annual_maintenance} onChange={handleInputChange} placeholder="15000" />
                        </div>
                        <div className="form-group">
                            <label>Fixed Sale Price (e.g. CCRC 80% Return)</label>
                            <input type="number" name="fixed_sale_price" value={formData.fixed_sale_price} onChange={handleInputChange} placeholder="Optional" />
                        </div>

                        <div className="form-group" style={{flexDirection: 'row', alignItems: 'center', marginTop: '1.5rem'}}>
                            <input type="checkbox" name="is_primary" checked={formData.is_primary} onChange={handleInputChange} style={{width: 'auto', marginRight: '0.5rem'}} />
                            <label style={{margin: 0, color: '#fff'}}>Principal Residence</label>
                        </div>
                        <div className="form-actions">
                             <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                             <button type="submit" className="btn-primary">Save Property</button>
                        </div>
                    </form>
                </div>
            )}

            {!showForm && properties.length < 12 && (
                <button className="btn-primary" onClick={startNewProperty} style={{marginBottom: '1rem'}}>+ Add Property</button>
            )}

            {isLoading ? <p>Loading real estate data...</p> : error ? <p>Error: {error}</p> : (
                <div className="property-list">
                    {properties.length === 0 ? <p>No properties tracked yet.</p> : 
                        properties.map(p => (
                            <PropertyCard key={p.property_id} property={p} onEdit={handleEdit} onDelete={handleDelete} />
                        ))
                    }
                </div>
            )}
        </div>
    );
};

export default RealEstateView;
