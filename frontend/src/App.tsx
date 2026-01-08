import { useEffect, useState } from 'react'

function App() {
  const [apiStatus, setApiStatus] = useState<string>('Checking...')

  useEffect(() => {
    fetch('http://127.0.0.1:8000/health')
      .then(res => res.json())
      .then(data => setApiStatus(`API: ${data.status} (${data.env})`))
      .catch(() => setApiStatus('API: Not connected'))
  }, [])

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">
          LinkedIn Outreach Agent
        </h1>
        <p className="text-gray-600 mb-2">MujerTech</p>
        <p className={`text-sm ${apiStatus.includes('healthy') ? 'text-green-600' : 'text-red-600'}`}>
          {apiStatus}
        </p>
      </div>
    </div>
  )
}

export default App