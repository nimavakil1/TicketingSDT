import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8003';

export interface MessageTemplate {
  id: number;
  template_id: string;
  name: string;
  recipient_type: 'supplier' | 'customer' | 'internal';
  language: string;
  subject_template: string;
  body_template: string;
  variables: string[];
  use_cases: string[];
  created_at: string;
  updated_at: string;
}

export interface MessageTemplateCreate {
  template_id: string;
  name: string;
  recipient_type: string;
  language: string;
  subject_template: string;
  body_template: string;
  variables?: string[];
  use_cases?: string[];
}

export interface MessageTemplateUpdate {
  name?: string;
  subject_template?: string;
  body_template?: string;
  variables?: string[];
  use_cases?: string[];
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  };
};

export const templatesApi = {
  /**
   * Get all templates with optional filters
   */
  getTemplates: async (params?: {
    recipient_type?: string;
    language?: string;
  }): Promise<MessageTemplate[]> => {
    const response = await axios.get(`${API_URL}/api/templates`, {
      ...getAuthHeaders(),
      params,
    });
    return response.data;
  },

  /**
   * Get a specific template by template_id
   */
  getTemplate: async (templateId: string): Promise<MessageTemplate> => {
    const response = await axios.get(
      `${API_URL}/api/templates/${templateId}`,
      getAuthHeaders()
    );
    return response.data;
  },

  /**
   * Create a new template
   */
  createTemplate: async (template: MessageTemplateCreate): Promise<MessageTemplate> => {
    const response = await axios.post(
      `${API_URL}/api/templates`,
      template,
      getAuthHeaders()
    );
    return response.data;
  },

  /**
   * Update an existing template
   */
  updateTemplate: async (
    templateId: string,
    updates: MessageTemplateUpdate
  ): Promise<MessageTemplate> => {
    const response = await axios.put(
      `${API_URL}/api/templates/${templateId}`,
      updates,
      getAuthHeaders()
    );
    return response.data;
  },

  /**
   * Delete a template
   */
  deleteTemplate: async (templateId: string): Promise<void> => {
    await axios.delete(
      `${API_URL}/api/templates/${templateId}`,
      getAuthHeaders()
    );
  },
};
