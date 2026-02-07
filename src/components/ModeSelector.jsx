import { useMode } from '../context/ModeContext';
import './ModeSelector.css';

const ModeSelector = () => {
    const { mode, setMode } = useMode();

    const toggleMode = () => {
        setMode(currentMode => (currentMode === 'actuals' ? 'demo' : 'actuals'));
    };

    return (
        <div 
            className={`mode-selector ${mode}`}
            onClick={toggleMode}
            title={`Click to switch to ${mode === 'actuals' ? 'Demo' : 'Live'} Mode`}
        >
            {mode === 'actuals' ? 'LIVE MODE' : 'DEMO MODE'}
        </div>
    );
};

export default ModeSelector;
