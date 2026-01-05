import './PlaceholderView.css';

const PlaceholderView = ({ viewName }) => {
    return (
        <div className="card placeholder-card">
            <h2>{viewName}</h2>
            <p>This section is under construction.</p>
            <p>Future capabilities will be implemented here as per the Project Requirements Specification.</p>
        </div>
    );
};

export default PlaceholderView;
