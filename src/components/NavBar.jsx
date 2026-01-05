import './NavBar.css';

const NavItem = ({ name, activeView, setActiveView }) => (
    <li 
        className={activeView === name ? 'active' : ''}
        onClick={() => setActiveView(name)}
    >
        {name}
    </li>
);

const NavBar = ({ activeView, setActiveView }) => {
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
        <nav className="navbar">
            <div className="logo">Curie Trust</div>
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
        </nav>
    );
};

export default NavBar;
