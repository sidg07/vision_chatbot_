import React, { useState } from "react";
import axios from "axios";

function App() {

  const [message, setMessage] = useState("");
  const [image, setImage] = useState(null);
  const [chat, setChat] = useState([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {

  if (!message && !image) return;

  const formData = new FormData();
  formData.append("message", message || "Analyze the image");

  if (image) {
    formData.append("image", image);
  }

  const userMsg = { role: "user", text: message };

  setChat(prev => [...prev, userMsg]);
  setLoading(true);

  try {

    const response = await axios.post(
      "http://localhost:8000/chat",
      formData
    );

    const botMsg = {
      role: "bot",
      text: response.data.response
    };

    setChat(prev => [...prev, botMsg]);

  } catch (error) {
    console.error(error);

    setChat(prev => [
      ...prev,
      { role: "bot", text: "⚠️ Error contacting server." }
    ]);
  } finally {

    setLoading(false);
    setMessage("");
    setImage(null);

  }
};

  return (

    <div className="min-h-screen bg-gray-100 flex flex-col items-center">

      <div className="w-full max-w-3xl bg-white shadow-xl rounded-xl mt-10 p-6">

        <h1 className="text-2xl font-bold text-center mb-6">
          🤖 Vision Chatbot
        </h1>

        {/* Chat Window */}

        <div className="h-96 overflow-y-auto space-y-4 border p-4 rounded-lg bg-gray-50">

          {chat.map((msg, index) => (

            <div
              key={index}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >

              <div
                className={`px-4 py-2 rounded-lg max-w-xs ${
                  msg.role === "user"
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200"
                }`}
              >
                {msg.text}
              </div>

            </div>

          ))}

          {loading && (
            <div className="text-gray-500 text-sm">
              Bot is thinking...
            </div>
          )}

        </div>

        {/* Image Upload */}

        <div className="mt-4 flex items-center gap-2">

          <input
            type="file"
            className="text-sm"
            onChange={(e) => setImage(e.target.files[0])}
          />

        </div>

        {/* Input Box */}

        <div className="mt-4 flex gap-2">

          <input
            className="flex-1 border rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask something..."
          />

          <button
            onClick={sendMessage}
            className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600"
          >
            Send
          </button>

        </div>

      </div>

    </div>
  );
}

export default App;