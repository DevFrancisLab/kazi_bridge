import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

// const isAuthenticated = () => {
//   const token = localStorage.getItem('token');
//   return !!token;
// };

interface ProtectedRouteProps {
  children: JSX.Element;
  allowedRole?: 'CLIENT' | 'FREELANCER';
}

const ProtectedRoute = ({ children, allowedRole }: ProtectedRouteProps) => {
  const auth = useAuth();
  if (!auth.isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const role = auth.role || (localStorage.getItem('role') as 'CLIENT' | 'FREELANCER' | null);
  if (!role) {
    return <Navigate to="/login" replace />;
  }

  const location = useLocation();
  const pathname = location.pathname;

  // Exact role match for each dashboard route
  if (pathname.startsWith('/client-dashboard')) {
    if (role !== 'CLIENT') {
      return <Navigate to="/freelancer-dashboard" replace />;
    }
    return children;
  }
  if (pathname.startsWith('/freelancer-dashboard')) {
    if (role !== 'FREELANCER') {
      return <Navigate to="/client-dashboard" replace />;
    }
    return children;
  }

  if (allowedRole && role !== allowedRole) {
    const redirectTarget = role === 'CLIENT' ? '/client-dashboard' : '/freelancer-dashboard';
    return <Navigate to={redirectTarget} replace />;
  }
  return children;
};

export default ProtectedRoute;
