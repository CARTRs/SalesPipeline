import http from './http'

export const authApi = {
  login: (data) => http.post('/auth/login', data),
}

export const userApi = {
  list: (params) => http.get('/users', { params }),
  get: (id) => http.get(`/users/${id}`),
  create: (data) => http.post('/users', data),
  update: (id, data) => http.put(`/users/${id}`, data),
}

export const opportunityApi = {
  list: (params) => http.get('/opportunities', { params }),
  get: (id) => http.get(`/opportunities/${id}`),
  create: (data) => http.post('/opportunities', data),
  update: (id, data) => http.put(`/opportunities/${id}`, data),
  delete: (id) => http.delete(`/opportunities/${id}`),
}
