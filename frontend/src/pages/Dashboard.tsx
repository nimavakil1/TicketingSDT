import React, { useEffect, useState } from 'react';
import { dashboardApi, DashboardStats } from '../api/dashboard';
import { messagesApi, MessageCount } from '../api/messages';
import {
  Mail,
  Ticket,
  AlertTriangle,
  Brain,
  TrendingUp,
  Clock,
  Activity,
  Send,
} from 'lucide-react';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [messageCount, setMessageCount] = useState<MessageCount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadStats();
    // Refresh every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const [statsData, messageData] = await Promise.all([
        dashboardApi.getStats(),
        messagesApi.getMessageCount(),
      ]);
      setStats(statsData);
      setMessageCount(messageData);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dashboard stats');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4">
        <p className="text-sm text-red-800">{error}</p>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Emails Processed Today',
      value: stats?.emails_processed_today || 0,
      icon: Mail,
      color: 'bg-blue-500',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-600',
    },
    {
      title: 'Active Tickets',
      value: stats?.tickets_active || 0,
      icon: Ticket,
      color: 'bg-green-500',
      bgColor: 'bg-green-50',
      textColor: 'text-green-600',
    },
    {
      title: 'Escalated Tickets',
      value: stats?.tickets_escalated || 0,
      icon: AlertTriangle,
      color: 'bg-red-500',
      bgColor: 'bg-red-50',
      textColor: 'text-red-600',
    },
    {
      title: 'AI Decisions Today',
      value: stats?.ai_decisions_today || 0,
      icon: Brain,
      color: 'bg-purple-500',
      bgColor: 'bg-purple-50',
      textColor: 'text-purple-600',
    },
    {
      title: 'Average Confidence',
      value: `${((stats?.average_confidence || 0) * 100).toFixed(1)}%`,
      icon: TrendingUp,
      color: 'bg-indigo-500',
      bgColor: 'bg-indigo-50',
      textColor: 'text-indigo-600',
    },
    {
      title: 'Retry Queue',
      value: stats?.emails_in_retry_queue || 0,
      icon: Clock,
      color: 'bg-yellow-500',
      bgColor: 'bg-yellow-50',
      textColor: 'text-yellow-600',
    },
  ];

  const getPhaseLabel = (phase: number) => {
    switch (phase) {
      case 1:
        return 'Shadow Mode';
      case 2:
        return 'Partial Automation';
      case 3:
        return 'Full Automation';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Real-time overview of your AI support agent</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-indigo-50 rounded-lg">
          <Activity className="h-5 w-5 text-indigo-600" />
          <span className="text-sm font-medium text-indigo-900">
            Phase {stats?.phase}: {getPhaseLabel(stats?.phase || 1)}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {statCards.map((card) => (
          <div key={card.title} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{card.title}</p>
                <p className="mt-2 text-3xl font-bold text-gray-900">{card.value}</p>
              </div>
              <div className={`p-3 rounded-lg ${card.bgColor}`}>
                <card.icon className={`h-6 w-6 ${card.textColor}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <a
            href="/messages"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
          >
            <Send className="h-5 w-5 text-indigo-500" />
            <div>
              <p className="font-medium text-gray-900">Pending Messages</p>
              <p className="text-sm text-gray-600">
                {messageCount?.total_pending || 0} messages to review
              </p>
              {messageCount && messageCount.low_confidence > 0 && (
                <p className="text-xs text-red-600 mt-1">
                  {messageCount.low_confidence} low confidence
                </p>
              )}
            </div>
          </a>
          <a
            href="/tickets?escalated=true"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
          >
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <div>
              <p className="font-medium text-gray-900">View Escalated Tickets</p>
              <p className="text-sm text-gray-600">
                {stats?.tickets_escalated || 0} tickets need attention
              </p>
            </div>
          </a>
          <a
            href="/emails"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
          >
            <Clock className="h-5 w-5 text-yellow-500" />
            <div>
              <p className="font-medium text-gray-900">Check Retry Queue</p>
              <p className="text-sm text-gray-600">
                {stats?.emails_in_retry_queue || 0} emails pending
              </p>
            </div>
          </a>
          <a
            href="/ai-decisions"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
          >
            <Brain className="h-5 w-5 text-purple-500" />
            <div>
              <p className="font-medium text-gray-900">Review AI Decisions</p>
              <p className="text-sm text-gray-600">Provide feedback for learning</p>
            </div>
          </a>
        </div>
      </div>

      {/* System Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">System Status</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 bg-green-500 rounded-full"></div>
              <span className="text-sm text-gray-700">API Server</span>
            </div>
            <span className="text-sm font-medium text-green-600">Operational</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 bg-green-500 rounded-full"></div>
              <span className="text-sm text-gray-700">AI Engine</span>
            </div>
            <span className="text-sm font-medium text-green-600">Active</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 bg-green-500 rounded-full"></div>
              <span className="text-sm text-gray-700">Email Monitor</span>
            </div>
            <span className="text-sm font-medium text-green-600">Running</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
