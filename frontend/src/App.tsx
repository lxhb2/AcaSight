import { ThemeProvider } from './contexts/ThemeContext';
import { AppProvider } from './contexts/AppContext';
import { ObsidianLayout } from './components/Layout/ObsidianLayout';
import { ErrorBoundary } from './components/Common/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AppProvider>
          <ObsidianLayout />
        </AppProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
