import axios from 'axios'

const axios_client = axios.create({
  baseURL: 'http://127.0.0.1:8000/',
})

/** DRF validation error format: { field_name: ["error message", ...], ... } */
type DRFValidationError = Record<string, string[]>

/** FastAPI wraps errors in { detail: ... } */
interface FastAPIErrorResponse {
  detail: DRFValidationError | string
}

/**
 * Extracts error message from Brain API responses.
 * Brain uses DRF format: {"field": ["error msg"]}
 * FastAPI wraps it in: {"detail": {"field": ["error msg"]}}
 */
export function extractErrorMessage(error: unknown): string {
  if (!axios.isAxiosError<FastAPIErrorResponse>(error)) {
    return String(error)
  }

  const detail = error.response?.data?.detail
  
  if (typeof detail === 'string') {
    return detail
  }
  
  if (detail && typeof detail === 'object') {
    // DRF validation errors: { field_name: ["message1", "message2"], ... }
    return Object.entries(detail)
      .map(([field, messages]) => `${field}: ${messages.join(', ')}`)
      .join('; ')
  }
  
  return error.message
}

const getState = async (sessionId: number, stateName: string) => {
  console.log('Getting state:', stateName)
  try {
    const response = await axios_client.get(`state/${sessionId}/${stateName}`)
    console.log('Response from backend for getting state:', response)
    return response.data
  } catch (error) {
    console.error('Error setting state:', error)
    return null
  }
}

const setState = async (sessionId: number, stateName: string, valuesDict: any) => {
  console.log('Setting state:', stateName)
  try {
    const response = await axios_client.post(`state/${sessionId}/${stateName}`, valuesDict)
    console.log('Response from backend:', response)
  } catch (error) {
    console.error('Error setting state:', error)
  }
}

const callWorker = async (sessionId: number, workerName: string) => {
  console.log('Calling worker')
  try {
    const response = await axios_client.get(`worker/${sessionId}/${workerName}`)
    console.log('Response from backend:', response)
    return response.data
  } catch (error) {
    console.error('Error calling worker:', error)
    throw error
  }
}


export interface BrainMetric {
  id: number
  short_name: string
  aliases: string[]
  toDisplay: () => string
}

// Frontend mapping types - combines data from file with brain metric/dimension selection
// Uses simple auto-incrementing IDs for table keys (generated on frontend only)
export interface MetricMapping {
  id: number
  dataMetric: string
  brainMetric: string
}

export interface DimensionMapping {
  id: number
  dataDimension: string
  brainDimension: string
}

const getBrainMetrics = async () => {
  console.log('Getting brain metrics')
  try {
    const response = await axios_client.get('metrics')
    console.log('Response from backend:', response)
    return response.data.map((metric: { id: number; short_name: string; aliases: string[] }) => ({
      id: metric.id,
      short_name: metric.short_name,
      aliases: metric.aliases,
      toDisplay: () =>
        `${metric.short_name}${metric.aliases?.length ? `  [${metric.aliases.join(', ')}]` : ''}`,
    })) as BrainMetric[]
  } catch (error) {
    console.error('Error getting brain metrics:', error)
  }
}

export interface BrainDimension {
  id: number
  short_name: string
  aliases: string[]
  toDisplay: () => string
}

const getBrainDimensions = async () => {
  console.log('Getting brain dimensions')
  try {
    const response = await axios_client.get('dimensions')
    console.log('Response from backend:', response)
    return response.data.map((dimension: { id: number; short_name: string; aliases: string[] }) => ({
      id: dimension.id,
      short_name: dimension.short_name,
      aliases: dimension.aliases,
      toDisplay: () =>
        `${dimension.short_name}${dimension.aliases?.length ? `  [${dimension.aliases.join(', ')}]` : ''}`,
    })) as BrainDimension[]
  } catch (error) {
    console.error('Error getting brain dimensions:', error)
  }
}

export { axios_client, getState, setState, callWorker, getBrainMetrics, getBrainDimensions }
