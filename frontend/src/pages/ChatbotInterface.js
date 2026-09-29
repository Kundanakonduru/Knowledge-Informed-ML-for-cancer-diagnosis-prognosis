import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AdminLayout from '../components/AdminLayout';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '';

function ChatbotInterface() {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const predictionId = searchParams.get('predictionId');

  useEffect(() => {
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [predictionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadHistory = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = predictionId ? { prediction_id: predictionId, limit: 20 } : { limit: 20 };
      const response = await axios.get(`${API_URL}/api/chatbot/history`, {
        params,
        headers: { Authorization: `Bearer ${token}` }
      });
      setMessages(response.data.reverse());
    } catch (error) {
      console.error('Error loading history:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    // Add user message
    const newUserMessage = {
      query: userMessage,
      response: '',
      created_at: new Date().toISOString(),
      chat_id: Date.now()
    };
    setMessages(prev => [...prev, newUserMessage]);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/chatbot/query`,
        {
          query: userMessage,
          prediction_id: predictionId ? parseInt(predictionId) : null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Update with response
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1].response = response.data.response;
        updated[updated.length - 1].chat_id = response.data.chat_id;
        return updated;
      });
    } catch (error) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1].response = error.response?.data?.detail || 'Error: Could not get response';
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminLayout>
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-gray-900">Clinical Assistant</h2>
          <p className="mt-2 text-gray-600">Ask questions about predictions and cancer diagnosis</p>
        </div>

        <div className="flex-1 max-w-4xl mx-auto w-full flex flex-col">
        <div className="flex-1 bg-white rounded-lg shadow mb-4 p-6 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              <h3 className="text-lg font-semibold mb-2">Ask a question about cancer predictions</h3>
              <p className="text-sm">Try: "Why was this cancer predicted?" or "Which genes caused high risk?"</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg) => (
                <div key={msg.chat_id} className="space-y-2">
                  <div className="flex justify-end">
                    <div className="bg-indigo-100 rounded-lg p-3 max-w-2xl">
                      <p className="text-sm text-gray-900">{msg.query}</p>
                    </div>
                  </div>
                  {msg.response && (
                    <div className="flex justify-start">
                      <div className="bg-gray-100 rounded-lg p-3 max-w-2xl">
                        <p className="text-sm text-gray-800 whitespace-pre-wrap">{msg.response}</p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg p-3">
                    <p className="text-sm text-gray-600">Thinking...</p>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about predictions, genes, pathways..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            Send
          </button>
        </form>
        </div>
      </div>
    </AdminLayout>
  );
}

export default ChatbotInterface;
