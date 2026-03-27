import React, { useState } from 'react';
import './App.css';
import axios from 'axios';

function App() {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [chatHistory, setChatHistory] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setError('');
    
    try {
      // Add user message to chat
      const userMessage = { sender: 'user', text: query };
      setChatHistory(prev => [...prev, userMessage]);
      
      const response = await axios.post('/query', { query });
      
      // Add assistant response to chat
      const assistantMessage = { 
        sender: 'assistant', 
        text: response.data.response,
        sources: response.data.sources || []
      };
      
      setChatHistory(prev => [...prev, assistantMessage]);
      setResponse(response.data.response);
      setQuery('');
    } catch (err) {
      console.error('Error:', err);
      setError('Failed to get response. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Bharatiyam AI Assistant</h1>
      </header>
      
      <main className="chat-container">
        <div className="chat-messages">
          {chatHistory.length === 0 ? (
            <div className="welcome-message">
              <p>Welcome to Bharatiyam AI Assistant. Ask me anything about the documents!</p>
            </div>
          ) : (
            chatHistory.map((msg, index) => (
              <div key={index} className={`message ${msg.sender}`}>
                <div className="message-content">
                  <div className="message-text">{msg.text}</div>
                  {/* {msg.sources && msg.sources.length > 0 && (
                    <div className="sources">
                      <div className="sources-title">Sources:</div>
                      <ul>
                        {msg.sources.map((source, i) => (
                          <li key={i} className="source-item">
                            <p className="source-content">{source.content}</p>
                            <div className="source-meta">
                              <span>Source: {source.metadata?.source || 'N/A'}</span>
                              <span>Page: {source.metadata?.page || 'N/A'}</span>
                              <span>Relevance: {source.score?.toFixed(2) || 'N/A'}</span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )} */}
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="message assistant">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
        </div>
        
        <form onSubmit={handleSubmit} className="chat-input">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask me anything..."
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !query.trim()}>
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </form>
        
        {error && <div className="error-message">{error}</div>}
      </main>
    </div>
  );
}

export default App;