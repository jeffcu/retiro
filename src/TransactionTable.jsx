import React from 'react';

const TransactionTable = ({ transactions }) => {
    if (!transactions || transactions.length === 0) {
        return <p>No transactions to display.</p>;
    }

    // Get headers from the keys of the first transaction object
    const headers = Object.keys(transactions[0]);

    return (
        <div className="table-container">
            <table>
                <thead>
                    <tr>
                        {headers.map(header => <th key={header}>{header}</th>)}
                    </tr>
                </thead>
                <tbody>
                    {transactions.map((tx, index) => (
                        <tr key={tx.transaction_id || index}>
                            {headers.map(header => <td key={header}>{String(tx[header])}</td>)}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default TransactionTable;