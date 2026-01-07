import './SideBar.css';

const NavItem = ({ name, activeView, setActiveView }) => (
    <li
        className={activeView === name ? 'active' : ''}
        onClick={() => setActiveView(name)}
    >
        {name}
    </li>
);

const SideBar = ({ activeView, setActiveView }) => {
    const navItems = [
        'Home',
        'Cashflow',
        'Portfolio',
        'Projects/Tags',
        'Real Estate',
        'Forecast',
        'Data & Settings',
    ];

    return (
        <nav className="sidebar">
            <div className="logo">
                Curie Trust
            </div>
            <ul>
                {navItems.map(item => (
                    <NavItem
                        key={item}
                        name={item}
                        activeView={activeView}
                        setActiveView={setActiveView}
                    />
                ))}
            </ul>
            <div className="sidebar-footer">
                <p>v0.0.1</p>
            </div>
        </nav>
    );
};

export default SideBar;
