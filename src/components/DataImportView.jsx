import { useState, useEffect } from 'react';
import './DataImportView.css';
import ImportSummary from './ImportSummary';
import RulesEditor from './RulesEditor';
import IncomeSankeySettings from './IncomeSankeySettings';

const FileUploader = ({ title, importType, onUploadSuccess }) => {
    const [file, setFile] = useState(null);
    const [accountId, setAccountId] = useState('');
    const [message, setMessage] = useState('');
    const [isError, setIsError] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    const handleFileChange = (e) => setFile(e.target.files[0]);

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
            const endpoint = importType === 'transactions' ? '/api/import/transactions' : '/api/import/holdings';
            const response = await fetch(endpoint, { method: 'POST', body: formData });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || 'Upload failed');

            setMessage(result.message);
            setFile(null);
            e.target.reset();
            onUploadSuccess();
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
                    <input type="text" id={`${importType}-account-id`} placeholder="e.g., brokerage, checking" onChange={(e) => setAccountId(e.target.value)} required />
                </div>
                <div className="form-group">
                    <label htmlFor={`${importType}-file`}>CSV File</label>
                    <input type="file" id={`${importType}-file`} accept=".csv" onChange={handleFileChange} required />
                </div>
                <button type="submit" disabled={isUploading}>{isUploading ? 'Uploading...' : 'Upload'}</button>
            </form>
            {message && <p className={`message ${isError ? 'error' : 'success'}`}>{message}</p>}
        </div>
    );
};

const AccountVisibilityManager = ({ onSettingsChanged }) => {
    const [accounts, setAccounts] = useState([]);
    const [visibility, setVisibility] = useState({});
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                const [accountsRes, visibilityRes] = await Promise.all([fetch('/api/accounts'), fetch('/api/accounts/visibility')]);
                if (!accountsRes.ok || !visibilityRes.ok) throw new Error("Failed to fetch account data");

                const accountsData = await accountsRes.json();
                const visibilityData = await visibilityRes.json();

                setAccounts(accountsData);
                setVisibility(accountsData.reduce((acc, id) => ({ ...acc, [id]: visibilityData.hasOwnProperty(id) ? visibilityData[id] : true }), {}));
            } catch (error) {
                console.error("Failed to fetch account settings", error);
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleToggle = (accountId) => setVisibility(prev => ({ ...prev, [accountId]: !prev[accountId] }));

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const response = await fetch('/api/accounts/visibility', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ settings: visibility }) });
            if (!response.ok) throw new Error('Failed to save settings');
            alert('Visibility settings saved successfully!');
            onSettingsChanged();
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className='visibility-manager-card'>
            <h3>Account Visibility (for Sankey Chart)</h3>
            {isLoading ? <p>Loading accounts...</p> : (
                <>
                    <div className='account-list'>
                        {accounts.map(id => (
                            <div key={id} className='account-item'>
                                <input type="checkbox" id={`vis-${id}`} checked={visibility[id] || false} onChange={() => handleToggle(id)} />
                                <label htmlFor={`vis-${id}`}>{id}</label>
                            </div>
                        ))}
                    </div>
                    <div className='visibility-actions'>
                        <button onClick={handleSave} disabled={isSaving}>{isSaving ? 'Saving...' : 'Save Settings'}</button>
                    </div>
                </>
            )}
        </div>
    );
};

const DataImportView = () => {
    const [refreshKey, setRefreshKey] = useState(0);
    const handleRefresh = () => setRefreshKey(prevKey => prevKey + 1);

    return (
        <>
            <div className="card">
                <h2>Data Importers</h2>
                <div className="importer-container">
                    <FileUploader title="Import Transactions" importType="transactions" onUploadSuccess={handleRefresh} />
                    <FileUploader title="Import Portfolio Holdings" importType="holdings" onUploadSuccess={handleRefresh} />
                </div>
            </div>
            <div className="card">
                <h2>Chart & Display Settings</h2>
                 <AccountVisibilityManager onSettingsChanged={handleRefresh} />
                 <IncomeSankeySettings onSettingsChanged={handleRefresh} />
            </div>
            <RulesEditor />
            <ImportSummary refreshKey={refreshKey} />
        </>
    );
};

export default DataImportView;