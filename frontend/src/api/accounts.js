/**
 * Accounts API — profile, onboarding, password change
 */
import client from './client';

const accountsApi = {
  getProfile: () =>
    client.get('/accounts/profile/'),

  updateProfile: (data) =>
    client.put('/accounts/profile/', data),

  updateUser: (data) =>
    client.put('/accounts/profile/update/', data),

  saveOnboarding: (data) =>
    client.post('/accounts/onboarding/', data),

  changePassword: (oldPassword, newPassword) =>
    client.post('/accounts/change-password/', {
      old_password: oldPassword,
      new_password: newPassword,
    }),
};

export default accountsApi;
