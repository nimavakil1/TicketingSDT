import client from './client';

export interface Ticket {
  ticket_number: string;
  status: string;
  customer_email: string;
  last_updated: string;
  escalated: boolean;
  ai_decision_count: number;
  ticket_status_id: number;
  owner_id: number | null;
}

export interface TicketMessage {
  id: number;
  createdAt: string;
  messageText: string;
  messageType: string;
  isInternal: boolean;
  authorName: string | null;
  authorEmail: string | null;
}

export interface TicketDetail {
  ticket_number: string;
  ticket_id: number;
  status: string;
  customer_email: string;
  ticket_status_id: number;
  owner_id: number | null;
  escalated: boolean;
  escalation_reason: string | null;
  escalation_date: string | null;
  last_updated: string;
  created_at: string;
  messages: TicketMessage[];
  ai_decisions: AIDecision[];
}

export interface AIDecision {
  id: number;
  timestamp: string;
  detected_language: string | null;
  detected_intent: string | null;
  confidence_score: number | null;
  recommended_action: string;
  response_generated: string;
  action_taken: string;
  deployment_phase: number;
  feedback: string | null;
  feedback_notes: string | null;
}

export const ticketsApi = {
  getTickets: async (params?: {
    limit?: number;
    offset?: number;
    escalated_only?: boolean;
  }): Promise<Ticket[]> => {
    const response = await client.get('/api/tickets', { params });
    return response.data;
  },

  getTicketDetail: async (ticketNumber: string): Promise<TicketDetail> => {
    const response = await client.get(`/api/tickets/${ticketNumber}`);
    return response.data;
  },
};
