import axios from 'axios'

const axios_client = axios.create({
  baseURL: 'http://127.0.0.1:8000/',
  // timeout: 1000,
})

const getState = async (sessionId: Number, stateName: String) => {
  console.log('Getting state:', stateName)
  try {
    const response = await axios_client.get(`state/${sessionId}/${stateName}`)
    console.log('Response from backend for getting state:', response)
    return response.data
  } catch (error) {
    console.error('Error setting state:', error)
  }
}

const setState = async (sessionId: Number, stateName: Number, valuesDict: JSON) => {
  console.log('Setting state:', stateName)
  try {
    const response = await axios_client.post(`state/${sessionId}/${stateName}`, valuesDict)
    console.log('Response from backend:', response)
  } catch (error) {
    console.error('Error setting state:', error)
  }
}

const callWorker = async (sessionId: Number, workerName: String) => {
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

export { axios_client, getState, setState, callWorker }
