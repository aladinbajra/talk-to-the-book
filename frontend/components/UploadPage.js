import { useState } from 'react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function UploadPage({ onUploadComplete }) {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [userConsent, setUserConsent] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      const ext = selectedFile.name.split('.').pop().toLowerCase()
      if (!['pdf', 'txt', 'epub'].includes(ext)) {
        setError('Please upload a PDF, TXT, or ePub file')
        return
      }
      setFile(selectedFile)
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file')
      return
    }

    if (!userConsent) {
      setError('Please confirm you have the right to upload this book')
      return
    }

    setUploading(true)
    setError(null)
    setSuccess(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_consent', userConsent)

      const response = await axios.post(`${API_URL}/api/v1/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setSuccess(`Book uploaded successfully! Book ID: ${response.data.book_id}`)
      
      // Start ingest automatically
      await axios.post(`${API_URL}/api/v1/ingest/start`, {
        book_id: response.data.book_id,
      })

      setTimeout(() => {
        onUploadComplete(response.data.book_id)
      }, 2000)
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Upload failed. Please try again.'
      )
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Upload a Book</h2>

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select File (PDF, TXT, or ePub)
          </label>
          <input
            type="file"
            accept=".pdf,.txt,.epub"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            disabled={uploading}
          />
          {file && (
            <p className="mt-2 text-sm text-gray-600">
              Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          )}
        </div>

        <div className="mb-6">
          <label className="flex items-start">
            <input
              type="checkbox"
              checked={userConsent}
              onChange={(e) => setUserConsent(e.target.checked)}
              className="mt-1 mr-2"
              disabled={uploading}
            />
            <span className="text-sm text-gray-700">
              I confirm I have the right to upload this book for personal Q&A
              purposes and understand that embeddings will be stored for 180 days
              unless I delete the book.
            </span>
          </label>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {success && (
          <div className="mb-4 bg-green-50 border border-green-200 rounded-md p-4">
            <p className="text-green-800 text-sm">{success}</p>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={uploading || !file || !userConsent}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? 'Uploading...' : 'Upload and Process'}
        </button>
      </div>

      <div className="mt-6 text-sm text-gray-600">
        <p className="mb-2">
          <strong>Note:</strong> The book will be processed automatically after
          upload. This may take several minutes depending on the book size.
        </p>
        <p>
          Supported formats: PDF, TXT, ePub (max 100MB)
        </p>
      </div>
    </div>
  )
}
