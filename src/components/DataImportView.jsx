import { useState, useEffect } from 'react';
import './DataImportView.css';
import ImportSummary from './ImportSummary';
import RulesEditor from './RulesEditor';
import IncomeSankeySettings from './IncomeSankeySettings';
import TaxFactsEditor from "./TaxFactsEditor.jsx"; 
import FutureIncomeStreamEditor from './FutureIncomeStreamEditor.jsx';
import PortfolioSnapshotManager from './PortfolioSnapshotManager';

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
        }
        finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="file-uploader-card">
            <h3>{title}</h3>
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label htmlFor={`${importType}-account-id`}>Account ID (Group Name)</label>
                    <input type="text" id={`${importType}-account-id`} placeholder="e.g., Fidelity, Chase" onChange={(e) => setAccountId(e.target.value)} required />
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

// --- NEW: AccountTaxStatusManager with Asset Totals & Grouping --- //
const AccountTaxStatusManager = () => {
    const [accounts, setAccounts] = useState([]);
    const [metadata, setMetadata] = useState({});
    const [performance, setPerformance] = useState({});
    const [isLoading, setIsLoading] = useState(true);
    const [savingId, setSavingId] = useState(null);

    const formatCurrency = (value) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value || 0);

    useEffect(() => {
        const fetchData = async () => {
            setIsLoading(true);
            try {
                const [accRes, metaRes, perfRes] = await Promise.all([
                    fetch('/api/accounts'),
                    fetch('/api/accounts/metadata'),
                    fetch('/api/accounts/performance')
                ]);
                
                const accData = await accRes.json();
                const metaData = await metaRes.json();
                const perfData = await perfRes.json();

                // Create a map of account_id/lookup_key to market value
                const perfMap = {};
                perfData.forEach(p => {
                    perfMap[p.lookup_key] = p.total_market_value;
                    // Also map the group_id if no specific key exists
                    if (!perfMap[p.group_id]) perfMap[p.group_id] = 0;
                });

                setAccounts(accData);
                setMetadata(metaData);
                setPerformance(perfMap);
            } catch (error) {
                console.error("Failed to load account data", error);
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleStatusChange = async (accountId, newStatus, newGroup = null) => {
        const currentMeta = metadata[accountId] || {};
        
        const updatedMeta = { 
            ...currentMeta, 
            tax_status: newStatus !== null ? newStatus : currentMeta.tax_status,
            group_name: newGroup !== null ? newGroup : currentMeta.group_name
        };
        
        // Optimistic UI update
        setMetadata(prev => ({ ...prev, [accountId]: updatedMeta }));
        
        setSavingId(accountId);
        try {
            await fetch(`/api/accounts/${accountId}/metadata`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    tax_status: updatedMeta.tax_status, 
                    notes: currentMeta.notes,
                    group_name: updatedMeta.group_name 
                })
            });
        } catch (error) {
            console.error("Save failed", error);
            alert("Failed to save tax status.");
        } finally {
            setSavingId(null);
        }
    };

    return (
        <div className="visibility-manager-card" style={{marginTop: '2rem'}}>
            <h3>Account Settings & Tax Status</h3>
            {isLoading ? <p>Loading...</p> : (
                <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.9em'}}>
                    <thead>
                        <tr style={{borderBottom: '1px solid #444', textAlign: 'left'}}>
                            <th style={{padding: '8px'}}>Account ID</th>
                            <th style={{padding: '8px', textAlign: 'right'}}>Asset Value</th>
                            <th style={{padding: '8px'}}>Tax Status</th>
                            <th style={{padding: '8px'}}>Group Name</th>
                        </tr>
                    </thead>
                    <tbody>
                        {accounts.map(acc => {
                            // Determine if this account has assets associated with it
                            const value = performance[acc] || 0;
                            const hasAssets = value > 0;
                            const textColor = hasAssets ? 'var(--gold-accent)' : '#666';
                            
                            return (
                                <tr key={acc} style={{borderBottom: '1px solid #444'}}>
                                    <td style={{padding: '8px', color: textColor}}>
                                        {acc}
                                        {!hasAssets && <span style={{fontSize: '0.8em', marginLeft: '8px', fontStyle: 'italic', opacity: 0.7}}>(No Assets)</span>}
                                    </td>
                                    <td style={{padding: '8px', textAlign: 'right', fontFamily: 'monospace', color: textColor}}>
                                        {formatCurrency(value)}
                                    </td>
                                    <td style={{padding: '8px'}}>
                                        <select 
                                            value={metadata[acc]?.tax_status || 'Taxable'}
                                            onChange={(e) => handleStatusChange(acc, e.target.value, null)}
                                            style={{padding: '4px', background: '#333', color: '#fff', border: '1px solid #555', borderRadius: '4px'}}
                                            disabled={savingId === acc}
                                        >
                                            <option value="Taxable">Taxable (Standard)</option>
                                            <option value="Deferred">Tax-Deferred (IRA/401k)</option>
                                            <option value="Roth">Tax-Free (Roth)</option>
                                            <option value="Exempt">Exempt (HSA/Other)</option>
                                        </select>
                                    </td>
                                    <td style={{padding: '8px'}}>
                                        <input
                                            type="text"
                                            placeholder="Group Name"
                                            value={metadata[acc]?.group_name || ''}
                                            onChange={(e) => setMetadata(prev => ({
                                                ...prev, 
                                                [acc]: { ...prev[acc], group_name: e.target.value }
                                            }))}
                                            onBlur={(e) => handleStatusChange(acc, null, e.target.value)}
                                            style={{width: '100%', padding: '4px', background: '#333', color: '#fff', border: '1px solid #555', borderRadius: '4px'}}
                                            disabled={savingId === acc}
                                        />
                                        {savingId === acc && <span style={{marginLeft: '8px', fontSize: '0.8em', color: '#aaa'}}>Saving...</span>}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            )}
        </div>
    );
};

const BackupManager = () => {
    const [isRestoring, setIsRestoring] = useState(false);
    const [restoreFile, setRestoreFile] = useState(null);

    const handleDownload = () => {
        window.open('/api/admin/backup', '_blank');
    };

    const handleRestore = async (e) => {
        e.preventDefault();
        if (!restoreFile) return;
        
        if (!confirm("WARNING: This will overwrite your entire database with the selected backup file. This action cannot be undone. Are you sure?")) {
            return;
        }

        setIsRestoring(true);
        const formData = new FormData();
        formData.append('file', restoreFile);

        try {
            const response = await fetch('/api/admin/restore', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Restore failed');
            }
            
            alert("Database restored successfully. The page will now reload.");
            window.location.reload();
        } catch (error) {
            alert(`Restore Error: ${error.message}`);
        } finally {
            setIsRestoring(false);
        }
    };

    const handleFactoryReset = async () => {
        if (!confirm("☢️ CRITICAL WARNING ☢️\n\nThis will permanently vaporize ALL transactions, holdings, properties, and custom rules. This action CANNOT be undone.\n\nAre you absolutely sure you want to wipe the database?")) {
            return;
        }
        setIsRestoring(true);
        try {
            const response = await fetch('/api/admin/factory-reset', { method: 'POST' });
            if (!response.ok) throw new Error('Factory reset failed');
            alert('Database wiped clean. The calibration matrix has been reset. Reloading...');
            window.location.reload();
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            setIsRestoring(false);
        }
    };

    return (
        <div className="backup-card">
            <h3>System Backup & Restore</h3>
            <div className="backup-actions">
                <div className="backup-section">
                    <p>Download a snapshot of the current database.</p>
                    <button className="backup-btn" onClick={handleDownload}>⬇ Download Database Snapshot</button>
                </div>
                <div className="backup-section restore-zone">
                    <p style={{color: '#ff9a9a'}}>Dangerous: Overwrite or wipe current data.</p>
                    <form onSubmit={handleRestore} className="restore-input-group">
                        <input 
                            type="file" 
                            accept=".db,.sqlite" 
                            onChange={(e) => setRestoreFile(e.target.files[0])} 
                            required
                            style={{width: 'auto', flexGrow: 1}}
                        />
                        <button type="submit" className="restore-btn" disabled={isRestoring}>
                            {isRestoring ? 'Restoring...' : '⬆ Restore'}
                        </button>
                    </form>
                    <button 
                        type="button" 
                        onClick={handleFactoryReset} 
                        disabled={isRestoring}
                        style={{marginTop: '0.5rem', width: '100%', backgroundColor: 'transparent', color: '#ff6b6b', border: '1px solid #ff6b6b', padding: '0.6rem 1rem', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold'}}
                    >
                        ☢️ Factory Reset (Wipe All Data)
                    </button>
                </div>
            </div>
        </div>
    );
}

const AccountVisibilityManager = ({ onSettingsChanged }) => {
    const [accounts, setAccounts] = useState([]);
    const [visibility, setVisibility] = useState({});
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    useState(() => {
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

const PortfolioSettings = () => {
    const [inceptionDate, setInceptionDate] = useState('');
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchDate = async () => {
            try {
                const response = await fetch('/api/settings/portfolio-inception-date');
                if (response.ok) {
                    const data = await response.json();
                    if (data) setInceptionDate(data);
                }
            } catch (error) {
                console.error("Failed to fetch inception date", error);
            } finally {
                setIsLoading(false);
            }
        };
        fetchDate();
    }, []);

    const handleSave = async () => {
        if (!inceptionDate) {
            alert("Please select a date.");
            return;
        }
        try {
            const response = await fetch('/api/settings/portfolio-inception-date', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ inception_date: inceptionDate })
            });
            if (!response.ok) throw new Error("Failed to save date");
            alert("Inception date saved!");
        } catch (error) {
            console.error(error);
            alert("Error saving date.");
        }
    };
    
    return (
        <div className="income-settings-card">
            <h3>Portfolio Inception Date</h3>
            <p>Set the date your portfolio was consolidated. This date is the official start for all performance calculations.</p>
            <div className="form-group" style={{ maxWidth: '300px', marginBottom: '1rem' }}>
                <label>Inception Date</label>
                <input type="date" value={inceptionDate} onChange={e => setInceptionDate(e.target.value)} disabled={isLoading} />
            </div>
            <div className="settings-actions">
                <button onClick={handleSave} disabled={isLoading}>Save Inception Date</button>
            </div>
        </div>
    )
}

const DataImportView = () => {
    const [refreshKey, setRefreshKey] = useState(0);
    const handleRefresh = () => setRefreshKey(prevKey => prevKey + 1);

    return (
        <>
             <div className="card">
                <h2>System Maintenance</h2>
                <BackupManager />
            </div>

            <div className="card">
                <h2>Data Importers</h2>
                <div className="importer-container">
                    <FileUploader title="Import Transactions" importType="transactions" onUploadSuccess={handleRefresh} />
                    <FileUploader title="Import Portfolio Holdings" importType="holdings" onUploadSuccess={handleRefresh} />
                </div>
            </div>

            <div className="card">
                <h2>Portfolio Settings</h2>
                <AccountTaxStatusManager />
                <PortfolioSettings />
                <PortfolioSnapshotManager />
            </div>

            <div className="card">
                <h2>Chart & Display Settings</h2>
                 <AccountVisibilityManager onSettingsChanged={handleRefresh} />
                 <IncomeSankeySettings onSettingsChanged={handleRefresh} />
            </div>

            <div className="card">
                <h2>Personal Inputs</h2>
                <TaxFactsEditor />
                <FutureIncomeStreamEditor />
            </div>

            <RulesEditor />
            <ImportSummary refreshKey={refreshKey} />
        </>
    );
};

export default DataImportView;
