/**
 * Chatbot API — settings, conversations, messages
 */
import client from './client';

const chatbotApi = {
  getSettings: () =>
    client.get('/chatbot/settings/'),

  updateSettings: (data) =>
    client.put('/chatbot/settings/', data),

  listConversations: (params = {}) =>
    client.get('/chatbot/conversations/', { params }),

  getConversation: (id) =>
    client.get(`/chatbot/conversations/${id}/`),

  listMessages: (conversationId) =>
    client.get(`/chatbot/conversations/${conversationId}/messages/`),
};

export default chatbotApi;
