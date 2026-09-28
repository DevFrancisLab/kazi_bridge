import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { loginUser } from '@/lib/auth';
import { Button } from '@/components/ui/button';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const auth = useAuth();

  const successMessage = location.state?.message;

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setLoading(true);

    const result = await loginUser({ email, password });
    setLoading(false);

    if (!result.success) {
      setError(result.message || 'Login failed.');
      console.error('Login failed:', result);
      return;
    }

    const token = result.data?.access;
    if (!token) {
      setError('No token received from server.');
      console.error('No token in response:', result.data);
      return;
    }
    const userRole = result.data?.role as 'CLIENT' | 'FREELANCER' | '';
    const userEmail = result.data?.email || '';
    
    console.log('Login successful, calling auth.login with:', { token: token.substring(0, 20) + '...', userRole, userEmail });
    
    auth.login({ token, role: userRole, email: userEmail });

    // Verify token was stored
    const storedToken = localStorage.getItem('token');
    console.log('After auth.login, token in localStorage:', storedToken ? 'present' : 'missing');

    // Read role from localStorage for redirect
    const storedRole = userRole;
    if (storedRole === 'CLIENT') {
      navigate('/client-dashboard');
      return;
    }
    if (storedRole === 'FREELANCER') {
      navigate('/freelancer-dashboard');
      return;
    }

    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
        <h1 className="mb-6 text-2xl font-bold text-slate-900">Login</h1>

  {successMessage && <p className="mb-3 rounded-md bg-green-100 p-3 text-sm text-green-700">{successMessage}</p>}

  {error && <p className="mb-3 rounded-md bg-red-100 p-3 text-sm text-red-700">{error}</p>}
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
            />
          </div>

          <div className="mb-6">
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
            />
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-600">
          Don't have an account?{' '}
          <Link to="/signup" className="text-blue-600 hover:text-blue-800">
            Sign up here
          </Link>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
