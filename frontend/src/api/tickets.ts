import client from './client';

export interface Ticket {
  ticket_number: string;
  status: string;
  customer_email: string;
  customer_name: string | null;
  order_number: string | null;
  purchase_order_number: string | null;
  last_updated: string;
  escalated: boolean;
  ai_decision_count: number;
  ticket_status_id: number;
  owner_id: number | null;
  custom_status_id: number | null;
  custom_status: CustomStatus | null;
}

export interface CustomStatus {
  id: number;
  name: string;
  color: string;
  is_closed: boolean;
  display_order: number;
}

export interface TicketMessage {
  id: number;
  gmail_message_id: string | null;
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
  customer_name?: string;
  customer_address?: string;
  customer_city?: string;
  customer_postal_code?: string;
  customer_country?: string;
  customer_phone?: string;
  order_number?: string;
  order_total?: number;
  order_currency?: string;
  order_date?: string;
  purchase_order_number?: string;
  tracking_number?: string;
  tracking_url?: string;
  carrier_name?: string;
  delivery_status?: string;
  expected_delivery_date?: string;
  product_details?: string; // JSON string
  supplier_name?: string;
  supplier_email?: string;
  supplier_phone?: string;
  supplier_contact_person?: string;
  ticket_status_id: number;
  owner_id: number | null;
  escalated: boolean;
  escalation_reason: string | null;
  escalation_date: string | null;
  last_updated: string;
  created_at: string;
  messages: TicketMessage[];
  ai_decisions: AIDecision[];
  custom_status_id: number | null;
  custom_status: CustomStatus | null;
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

export interface Attachment {
  id: number;
  ticket_id: number;
  filename: string;
  original_filename: string;
  file_path: string;
  mime_type: string | null;
  file_size: number | null;
  extraction_status: string;
  extracted_text: string | null;
  created_at: string;
  gmail_message_id: string | null;
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

  refreshTicket: async (ticketNumber: string): Promise<any> => {
    const response = await client.post(`/api/tickets/${ticketNumber}/refresh`);
    return response.data;
  },

  getAttachments: async (ticketNumber: string): Promise<Attachment[]> => {
    const response = await client.get(`/api/tickets/${ticketNumber}/attachments`);
    return response.data;
  },

  downloadAttachment: async (attachmentId: number): Promise<Blob> => {
    const response = await client.get(`/api/attachments/${attachmentId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  uploadAttachment: async (ticketNumber: string, file: File): Promise<Attachment> => {
    const formData = new FormData();
    formData.append('file', file);
    // Don't set Content-Type manually - let axios set it with proper boundary
    const response = await client.post(`/api/tickets/${ticketNumber}/attachments/upload`, formData);
    return response.data;
  },

  deleteAttachment: async (attachmentId: number): Promise<void> => {
    await client.delete(`/api/attachments/${attachmentId}`);
  },
};
