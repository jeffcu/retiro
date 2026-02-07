import { createContext, useState, useMemo, useContext } from 'react';

export const ModeContext = createContext();

export const useMode = () => {
    const context = useContext(ModeContext);
    if (context === undefined) {
        throw new Error('useMode must be used within a ModeProvider');
    }
    return context;
};

export const ModeProvider = ({ children }) => {
    const [mode, setMode] = useState('actuals'); // 'actuals' or 'demo'

    const value = useMemo(() => ({ mode, setMode }), [mode]);

    return (
        <ModeContext.Provider value={value}>
            {children}
        </ModeContext.Provider>
    );
};
