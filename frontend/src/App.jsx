import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import AdminPage from './pages/AdminPage';
import ExamPage from './pages/ExamPage';
import ResultPage from './pages/ResultPage';
import EvaluationPage from './pages/EvaluationPage';

function App() {
  return (
    <Router>
      <div className="app-container">
        <header className="app-header">
          <h1>Exam System</h1>
        </header>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/exam" element={<ExamPage />} />
            <Route path="/result" element={<ResultPage />} />
            <Route path="/admin/evaluate/:examId/:username" element={<EvaluationPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
