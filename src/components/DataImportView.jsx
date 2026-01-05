import { useState } from 'react';
import './DataImportView.css';

const FileUploader = ({ title, importType }) => {
    const [file, setFile] = useState(null);
    const [accountId, setAccountId] = useState('');
    const [message, setMessage] = useState('');
    const [isError, setIsError] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file || !accountId) {
            setMessage('Please select a file and enter an Account ID.');
            setIsError(true);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('account_id', accountId);

        setIsUploading(true);
        setMessage('');
        setIsError(false);

        try {
            const endpoint = importType === 'transactions' 
                ? '/api/import/transactions' 
                : '/api/import/holdings';

            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Upload failed');
            }

            setMessage(result.message);
            setFile(null);
            e.target.reset(); // Reset the form fields
        } catch (err) {
            setMessage(`Error: ${err.message}`);
            setIsError(true);
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="file-uploader-card">
            <h3>{title}</h3>
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label htmlFor={`${importType}-account-id`}>Account ID</label>
                    <input 
                        type="text" 
                        id={`${importType}-account-id`}
                        placeholder="e.g., brokerage, checking"
                        onChange={(e) => setAccountId(e.target.value)} 
                        required 
                    />
                </div>
                <div className="form-group">
                    <label htmlFor={`${importType}-file`}>CSV File</label>
                    <input 
                        type="file" 
                        id={`${importType}-file`}
                        accept=".csv" 
                        onChange={handleFileChange} 
                        required 
                    />
                </div>
                <button type="submit" disabled={isUploading}>{isUploading ? 'Uploading...' : 'Upload'}</button>
            </form>
            {message && (
                <p className={`message ${isError ? 'error' : 'success'}`}>{message}</p>
            )}
        </div>
    );
};

const DataImportView = () => {
    return (
        <div className="card">
            <h2>Data Importers</h2>
            <div className="importer-container">
                <FileUploader title="Import Transactions" importType="transactions" />
                <FileUploader title="Import Portfolio Holdings" importType="holdings" />
            </div>
        </div>
    );
};

export default DataImportView;
