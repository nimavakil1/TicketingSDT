import client from './client';

export interface DashboardStats {
  total_tickets: number;
  pending_messages: number;
  processed_emails: number;
  escalated_tickets: number;
  recent_activity: Array<{
    id: number;
    ticket_number: string;
    action: string;
    timestamp: string;
  }>;
}

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await client.get('/api/dashboard/stats');
    return response.data;
  },
};
