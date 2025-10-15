import client from './client';

export interface DashboardStats {
  emails_processed_today: number;
  tickets_active: number;
  tickets_escalated: number;
  ai_decisions_today: number;
  average_confidence: number;
  emails_in_retry_queue: number;
  phase: number;
}

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await client.get('/api/dashboard/stats');
    return response.data;
  },
};
