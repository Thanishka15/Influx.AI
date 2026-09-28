import { useState } from "react";

export default function InputBox({ onSend }) {
  const [value, setValue] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onSend(value);
    setValue("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center p-4 bg-gray-800 border-t border-gray-700"
    >
      <input
        type="text"
        placeholder="Type your message..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="flex-1 rounded-lg bg-gray-700 text-gray-200 placeholder-gray-400 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      <button
        type="submit"
        className="ml-3 flex items-center justify-center p-2 rounded-lg bg-blue-600 hover:bg-blue-500 transition-colors focus:outline-none"
        aria-label="Send message"
      >
        <svg
          className="w-5 h-5 text-white"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M14.752 11.168l-9.193 4.595a1 1 0 001.341 1.341l4.595-9.193m3.257 3.257L21 3m-6.248 8.168L21 3"
          />
        </svg>
      </button>
    </form>
  );
}