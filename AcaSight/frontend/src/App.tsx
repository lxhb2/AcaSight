import { ThemeProvider } from './contexts/ThemeContext';
import { AppProvider } from './contexts/AppContext';
import { ObsidianLayout } from './components/Layout/ObsidianLayout';

function App() {
  return (
    <ThemeProvider>
      <AppProvider>
        <ObsidianLayout />
      </AppProvider>
    </ThemeProvider>
  );
}

export default App;
