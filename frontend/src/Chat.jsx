import { useState } from "react";
import Message from "./Message";
import InputBox from "./InputBox";

export default function Chat() {
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello! How can I help you today?", from: "bot" },
    { id: 2, text: "I need some information about your pricing.", from: "user" },
  ]);

  const handleSend = (text) => {
    if (!text.trim()) return;
    const newMsg = {
      id: Date.now(),
      text,
      from: "user",
    };
    setMessages((prev) => [...prev, newMsg]);

    // Simulate a bot reply after a short delay
    setTimeout(() => {
      const botReply = {
        id: Date.now() + 1,
        text: "Sure! Our pricing plans start at $9/month.",
        from: "bot",
      };
      setMessages((prev) => [...prev, botReply]);
    }, 800);
  };

  return (
    <div className="flex flex-col flex-1 h-full bg-gray-900">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <Message key={msg.id} text={msg.text} from={msg.from} />
        ))}
      </div>

      {/* Input area */}
      <InputBox onSend={handleSend} />
    </div>
  );
}