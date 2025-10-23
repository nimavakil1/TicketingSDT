import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Emails from './pages/Emails';
import Tickets from './pages/Tickets';
import TicketDetail from './pages/TicketDetail';
import PendingMessages from './pages/PendingMessages';
import AIDecisions from './pages/AIDecisions';
import Feedback from './pages/Feedback';
import Settings from './pages/Settings';

const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout>
              <Dashboard />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/emails"
        element={
          <PrivateRoute>
            <Layout>
              <Emails />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/tickets"
        element={
          <PrivateRoute>
            <Layout>
              <Tickets />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/tickets/:ticketNumber"
        element={
          <PrivateRoute>
            <Layout>
              <TicketDetail />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/pending-messages"
        element={
          <PrivateRoute>
            <Layout>
              <PendingMessages />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/ai-decisions"
        element={
          <PrivateRoute>
            <Layout>
              <AIDecisions />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/feedback"
        element={
          <PrivateRoute>
            <Layout>
              <Feedback />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <PrivateRoute>
            <Layout>
              <Settings />
            </Layout>
          </PrivateRoute>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
