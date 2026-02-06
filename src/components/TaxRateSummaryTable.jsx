import { useState, useEffect } from 'react';
import './TaxRateSummaryTable.css';

const TaxRateSummaryTable = () => {
    const [taxData, setTaxData] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchTaxData = async () => {
            try {
                setIsLoading(true);
                const response = await fetch('/api/analysis/effective-tax-rates');
                if (!response.ok) {
                    throw new Error('Failed to fetch tax rate data');
                }
                const data = await response.json();
                setTaxData(data);
            } catch (err) {
                setError(err.message);
                console.error(err);
            } finally {
                setIsLoading(false);
            }
        };
        fetchTaxData();
    }, []);

    return (
        <div className="card tax-summary-card">
            <h2>Effective Tax Rates</h2>
            {isLoading ? (
                <p>Calculating rates...</p>
            ) : error ? (
                <p className="error-message">Error: {error}</p>
            ) : (
                <table className="summary-table">
                    <thead>
                        <tr>
                            <th>Tax Year</th>
                            <th>Effective Federal Rate</th>
                            <th>Effective State Rate</th>
                            <th>Effective Combined Rate</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {taxData.map(row => (
                            <tr key={row.year}>
                                <td><strong>{row.year}</strong></td>
                                <td>{row.federal_rate}</td>
                                <td>{row.state_rate}</td>
                                <td>{row.combined_rate}</td>
                                <td className="notes-cell">{row.notes}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
};

export default TaxRateSummaryTable;
