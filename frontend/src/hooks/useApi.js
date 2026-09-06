/**
 * useApi — generic data-fetching hook with loading/error states.
 *
 * Usage:
 *   const { data, loading, error, execute } = useApi(ordersApi.list);
 *   // Auto-fetch on mount:
 *   const { data, loading, error } = useApi(ordersApi.list, { immediate: true });
 */
import { useState, useCallback, useEffect } from 'react';
import { getErrorMessage } from '../api/client';

export default function useApi(apiFunction, { immediate = false, params = null } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFunction(...args);
      setData(response.data);
      return response.data;
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction]);

  useEffect(() => {
    if (immediate) {
      if (params) {
        execute(params);
      } else {
        execute();
      }
    }
  }, [immediate]); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading, error, setData, execute };
}
