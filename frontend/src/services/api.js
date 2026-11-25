import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const getAssetUrl = (assetPath) => {
  if (!assetPath) return null;
  if (/^https?:\/\//i.test(assetPath)) return assetPath;
  if (/^https?:\/\//i.test(API_BASE_URL)) {
    return new URL(assetPath, new URL(API_BASE_URL).origin).toString();
  }
  return assetPath;
};

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 90000,
});

/**
 * Check backend system health status
 */
export const checkHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

/**
 * Upload a course PDF material and trigger text extraction via PyMuPDF
 * @param {File} file - PDF file object
 * @param {string} [projectId] - Optional project ID
 */
export const uploadDocument = async (file, projectId = null) => {
  const formData = new FormData();
  formData.append('file', file);
  if (projectId) {
    formData.append('project_id', projectId);
  }

  const response = await apiClient.post('/v1/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Fetch document details and full extracted text by ID
 * @param {string} documentId
 */
export const getDocument = async (documentId) => {
  const response = await apiClient.get(`/v1/documents/${documentId}`);
  return response.data;
};

/**
 * Coordinate LangGraph 5-agent pipeline to generate an educational diagram & illustration
 */
export const generateDiagram = async ({
  text_input,
  topic,
  document_id,
  diagram_type = 'flowchart',
  illustration_style = 'professional_educational',
  complexity_level = 'intermediate',
  generate_illustration = true,
  custom_focus,
  project_id,
  poster_settings
}) => {
  const response = await apiClient.post('/v1/generations/start', {
    text_input,
    topic,
    document_id,
    diagram_type,
    illustration_style,
    complexity_level,
    generate_illustration,
    custom_focus,
    project_id,
    poster_settings,
  });
  return response.data;
};

/**
 * Retrieve saved diagram generation by ID
 * @param {string} generationId
 */
export const getGeneration = async (generationId) => {
  const response = await apiClient.get(`/v1/generations/${generationId}`);
  return response.data;
};

/**
 * Retrieve list of all generations with optional search and filter
 */
export const listGenerations = async (params = {}) => {
  const response = await apiClient.get('/v1/generations', { params });
  return response.data;
};

/**
 * Retrieve aggregated dashboard statistics
 */
export const getGenerationStats = async () => {
  const response = await apiClient.get('/v1/generations/stats/summary');
  return response.data;
};

/**
 * Check agent progress and live logs by generation ID
 */
export const getGenerationStatus = async (generationId) => {
  const response = await apiClient.get(`/v1/generations/${generationId}/status`);
  return response.data;
};

/**
 * Delete a generation record and local assets
 */
export const deleteGeneration = async (generationId) => {
  const response = await apiClient.delete(`/v1/generations/${generationId}`);
  return response.data;
};

/**
 * Helper to construct export download URL
 */
export const getExportUrl = (generationId, formatType) => {
  return `${API_BASE_URL}/v1/generations/${generationId}/export/${formatType}`;
};

export default {
  checkHealth,
  uploadDocument,
  getDocument,
  generateDiagram,
  getGeneration,
  listGenerations,
  getGenerationStats,
  getGenerationStatus,
  deleteGeneration,
  getExportUrl,
  getAssetUrl,
};
