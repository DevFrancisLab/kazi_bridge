import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { signup, loginUser } from '@/lib/auth';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';

const SignupPage = () => {
  const [email, setEmail] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState<'CLIENT' | 'FREELANCER'>('CLIENT');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{[key: string]: string}>({});
  const navigate = useNavigate();
  const auth = useAuth();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setFieldErrors({});
    setLoading(true);

    // Basic validation
    if (!email || !password || !confirmPassword || !phoneNumber || !role) {
      setError('All fields are required.');
      setLoading(false);
      return;
    }

    // Confirm password validation
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      setLoading(false);
      return;
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('Please enter a valid email address.');
      setLoading(false);
      return;
    }

    // Password validation
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      setLoading(false);
      return;
    }

    const result = await signup({ email, password, phone_number: phoneNumber, role });
    setLoading(false);

    if (!result.success) {
      // Handle field-specific errors
      if (result.errors && typeof result.errors === 'object') {
        const errors: {[key: string]: string} = {};
        Object.entries(result.errors).forEach(([field, messages]) => {
          if (Array.isArray(messages)) {
            errors[field] = messages[0]; // Take first error message
          } else if (typeof messages === 'string') {
            errors[field] = messages;
          }
        });
        setFieldErrors(errors);
        
        // Set general error if no field-specific errors
        if (Object.keys(errors).length === 0) {
          setError(result.message || 'Registration failed.');
        }
      } else {
        setError(result.message || 'Registration failed.');
      }
      return;
    }

    // Registration successful
    // Automatically log in the user
    const loginResult = await loginUser({ email, password });
    
    if (loginResult.success) {
      // Store tokens in localStorage
      const token = loginResult.data?.access;
      if (token) {
        const loginRole = (loginResult.data?.role ?? role) as 'CLIENT' | 'FREELANCER' | '';
        const loginEmail = loginResult.data?.email ?? '';
        auth.login({ token, role: loginRole, email: loginEmail });
        
        // Read role from context for redirect
        const storedRole = auth.role;
        if (storedRole === 'CLIENT') {
          navigate('/client-dashboard');
        } else if (storedRole === 'FREELANCER') {
          navigate('/freelancer-dashboard');
        } else {
          navigate('/dashboard');
        }
      } else {
        // Fallback: redirect to login if no token received
        navigate('/login', { 
          state: { 
            message: 'Account created successfully, please login' 
          } 
        });
      }
    } else {
      // If auto-login fails, redirect to login page
      navigate('/login', { 
        state: { 
          message: 'Account created successfully, please login' 
        } 
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
        <h1 className="mb-6 text-2xl font-bold text-slate-900">Create Account</h1>

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
              className={`w-full rounded-md border px-3 py-2 focus:outline-none ${
                fieldErrors.email ? 'border-red-500 focus:border-red-500' : 'border-gray-300 focus:border-blue-500'
              }`}
              placeholder="Enter your email"
            />
            {fieldErrors.email && <p className="mt-1 text-sm text-red-600">{fieldErrors.email}</p>}
          </div>

          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="phoneNumber">
              Phone Number
            </label>
            <input
              id="phoneNumber"
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              required
              className={`w-full rounded-md border px-3 py-2 focus:outline-none ${
                fieldErrors.phone_number ? 'border-red-500 focus:border-red-500' : 'border-gray-300 focus:border-blue-500'
              }`}
              placeholder="Enter your phone number"
            />
            {fieldErrors.phone_number && <p className="mt-1 text-sm text-red-600">{fieldErrors.phone_number}</p>}
          </div>

          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className={`w-full rounded-md border px-3 py-2 focus:outline-none ${
                fieldErrors.password ? 'border-red-500 focus:border-red-500' : 'border-gray-300 focus:border-blue-500'
              }`}
              placeholder="Enter your password"
            />
            {fieldErrors.password && <p className="mt-1 text-sm text-red-600">{fieldErrors.password}</p>}
          </div>

          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="confirmPassword">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              className={`w-full rounded-md border px-3 py-2 focus:outline-none ${
                fieldErrors.confirmPassword ? 'border-red-500 focus:border-red-500' : 'border-gray-300 focus:border-blue-500'
              }`}
              placeholder="Confirm your password"
            />
            {fieldErrors.confirmPassword && <p className="mt-1 text-sm text-red-600">{fieldErrors.confirmPassword}</p>}
          </div>

          <div className="mb-6">
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="role">
              Role
            </label>
            <select
              id="role"
              value={role}
              onChange={(e) => setRole(e.target.value as 'CLIENT' | 'FREELANCER')}
              required
              className={`w-full rounded-md border px-3 py-2 focus:outline-none ${
                fieldErrors.role ? 'border-red-500 focus:border-red-500' : 'border-gray-300 focus:border-blue-500'
              }`}
            >
              <option value="CLIENT">Client</option>
              <option value="FREELANCER">Freelancer</option>
            </select>
            {fieldErrors.role && <p className="mt-1 text-sm text-red-600">{fieldErrors.role}</p>}
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Creating Account...' : 'Create Account'}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-600">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:text-blue-800">
            Login here
          </Link>
        </p>
      </div>
    </div>
  );
};

export default SignupPage;