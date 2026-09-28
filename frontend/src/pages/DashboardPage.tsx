import { Navigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

// Optional alias page for legacy /dashboard route. Redirect based on user role.
const DashboardPage = () => {
  const auth = useAuth();
  const role = auth.role;
  if (role === 'CLIENT') {
    return <Navigate to="/client-dashboard" replace />;
  }
  if (role === 'FREELANCER') {
    return <Navigate to="/freelancer-dashboard" replace />;
  }
  return <Navigate to="/login" replace />;
};

export default DashboardPage;
