import React from 'react';
import './ErrorBoundary.css';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error for diagnostics
    console.error("Uncaught error:", error, errorInfo);
    this.setState({
        error: error,
        errorInfo: errorInfo
    });
  }

  render() {
    if (this.state.hasError) {
      // Render fallback UI
      return (
        <div className="error-boundary-card">
            <h2>System Anomaly Detected</h2>
            <p>A critical error has occurred in a user interface component, causing a display failure.</p>
            <details>
                <summary>Diagnostic Details (for Engineering)</summary>
                <pre>
                    {this.state.error && this.state.error.toString()}
                    <br />
                    {this.state.errorInfo && this.state.errorInfo.componentStack}
                </pre>
            </details>
        </div>
      );
    }

    return this.props.children; 
  }
}

export default ErrorBoundary;
