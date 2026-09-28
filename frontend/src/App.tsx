import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./context/AuthContext";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Index from "./pages/Index.tsx";
import NotFound from "./pages/NotFound.tsx";
import LoginPage from "./pages/LoginPage.tsx";
import SignupPage from "./pages/SignupPage.tsx";
import ProtectedRoute from "@/components/ProtectedRoute";
import DashboardShell from "@/components/DashboardShell";
import DashboardPage from "./pages/DashboardPage";
import ClientDashboardPage from "./pages/ClientDashboardPage";
import FreelancerDashboardPage from "./pages/FreelancerDashboardPage";
import JobsPage from "./pages/JobsPage";
import JobDetailsPage from "./pages/JobDetailsPage";
import PaymentsPage from "./pages/PaymentsPage";
import MessagesPage from "./pages/MessagesPage";
import FindJobsPage from "./pages/FindJobsPage";
import TasksPage from "./pages/TasksPage";
import EarningsPage from "./pages/EarningsPage";
import ProfilePage from "./pages/ProfilePage";
import FreelancersPage from "./pages/FreelancersPage";

const queryClient = new QueryClient();

const App = () => (
  <AuthProvider>
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            element={
              <ProtectedRoute>
                <DashboardShell />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route
              path="/client-dashboard"
              element={
                <ProtectedRoute allowedRole="CLIENT">
                  <ClientDashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/freelancer-dashboard"
              element={
                <ProtectedRoute allowedRole="FREELANCER">
                  <FreelancerDashboardPage />
                </ProtectedRoute>
              }
            />
            {/* Client-only routes */}
            <Route
              path="/jobs"
              element={
                <ProtectedRoute allowedRole="CLIENT">
                  <JobsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/jobs/:id"
              element={
                <ProtectedRoute allowedRole="CLIENT">
                  <JobDetailsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/freelancers"
              element={
                <ProtectedRoute allowedRole="CLIENT">
                  <FreelancersPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/payments"
              element={
                <ProtectedRoute allowedRole="CLIENT">
                  <PaymentsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/messages"
              element={
                <ProtectedRoute allowedRole="CLIENT">
                  <MessagesPage />
                </ProtectedRoute>
              }
            />
            {/* Freelancer-only routes */}
            <Route
              path="/find-jobs"
              element={
                <ProtectedRoute allowedRole="FREELANCER">
                  <FindJobsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/tasks"
              element={
                <ProtectedRoute allowedRole="FREELANCER">
                  <TasksPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/earnings"
              element={
                <ProtectedRoute allowedRole="FREELANCER">
                  <EarningsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute allowedRole="FREELANCER">
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
          </Route>
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
  </AuthProvider>
);

export default App;
