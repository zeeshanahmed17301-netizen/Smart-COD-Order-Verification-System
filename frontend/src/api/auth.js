/**
 * Auth API — login, signup, token refresh
 */
import client from './client';

const authApi = {
  login: (email, password) =>
    client.post('/auth/login/', { email, password }),

  signup: ({ email, password, password2, firstName, lastName, username }) =>
    client.post('/auth/signup/', {
      email,
      password,
      password2,
      first_name: firstName,
      last_name: lastName,
      username: username || email.split('@')[0],
    }),

  refreshToken: (refresh) =>
    client.post('/auth/token/refresh/', { refresh }),

  requestPasswordReset: (email) =>
    client.post('/auth/password/reset/', { email }),

  confirmPasswordReset: ({ uid, token, newPassword }) =>
    client.post('/auth/password/reset/confirm/', {
      uid,
      token,
      new_password: newPassword,
    }),
};

export default authApi;
