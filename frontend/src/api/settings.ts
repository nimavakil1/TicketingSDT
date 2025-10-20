import client from './client';

export interface SystemSetting {
  key: string;
  value: string;
}

export const getSystemSetting = async (key: string): Promise<SystemSetting> => {
  const response = await client.get(`/api/settings/${key}`);
  return response.data;
};

export const updateSystemSetting = async (key: string, value: string): Promise<SystemSetting> => {
  const response = await client.put(`/api/settings/${key}`, null, {
    params: { value }
  });
  return response.data;
};
