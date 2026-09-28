export default function Message({ text, from }) {
  const isUser = from === "user";

  return (
    <div
      className={`
        flex 
        ${isUser ? "justify-end" : "justify-start"} 
        w-full
      `}
    >
      <div
        className={`
          max-w-xs md:max-w-md 
          rounded-lg 
          px-4 py-2 
          text-sm 
          ${isUser ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-200"}
        `}
      >
        {text}
      </div>
    </div>
  );
}