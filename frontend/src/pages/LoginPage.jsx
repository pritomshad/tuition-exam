import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

function LoginPage() {
  const [tab, setTab] = useState('student'); // 'student' or 'admin'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [examId, setExamId] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    try {
      if (tab === 'student') {
        const res = await api.post('/student/login', {
          username,
          password,
          exam_id: parseInt(examId)
        });
        localStorage.setItem('token', res.data.token);
        localStorage.setItem('role', 'student');
        navigate('/exam');
      } else {
        const res = await api.post('/admin/login', {
          username,
          password
        });
        localStorage.setItem('token', res.data.token);
        localStorage.setItem('role', 'admin');
        navigate('/admin');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed');
    }
  };

  return (
    <div className="card" style={{ maxWidth: '400px', margin: '4rem auto' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '2rem' }}>Login</h2>
      
      <div className="tabs">
        <div 
          className={`tab ${tab === 'student' ? 'active' : ''}`}
          onClick={() => { setTab('student'); setError(''); }}
          style={{ flex: 1, textAlign: 'center' }}
        >
          Student
        </div>
        <div 
          className={`tab ${tab === 'admin' ? 'active' : ''}`}
          onClick={() => { setTab('admin'); setError(''); }}
          style={{ flex: 1, textAlign: 'center' }}
        >
          Admin
        </div>
      </div>

      {error && <div className="error-msg">{error}</div>}

      <form onSubmit={handleLogin}>
        <div className="form-group">
          <label>Username</label>
          <input 
            type="text" 
            value={username} 
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Password</label>
          <input 
            type="password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {tab === 'student' && (
          <div className="form-group">
            <label>Exam ID</label>
            <input 
              type="number" 
              value={examId} 
              onChange={(e) => setExamId(e.target.value)}
              required
            />
          </div>
        )}

        <button type="submit">Login</button>
      </form>
    </div>
  );
}

export default LoginPage;
