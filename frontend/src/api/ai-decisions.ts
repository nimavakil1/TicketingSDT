import client from './client';

export interface AIDecisionInfo {
  id: number;
  ticket_number: string;
  timestamp: string;
  detected_language: string | null;
  detected_intent: string | null;
  confidence_score: number | null;
  action_taken: string;
  deployment_phase: number;
}

export const aiDecisionsApi = {
  getDecisions: async (params?: {
    limit?: number;
    offset?: number;
  }): Promise<AIDecisionInfo[]> => {
    const response = await client.get('/api/ai-decisions', { params });
    return response.data;
  },

  submitFeedback: async (
    decisionId: number,
    feedback: string,
    notes?: string
  ): Promise<{ success: boolean; message: string }> => {
    const response = await client.post(
      `/api/ai-decisions/${decisionId}/feedback`,
      { feedback, notes }
    );
    return response.data;
  },
};
