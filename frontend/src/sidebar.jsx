export default function Sidebar({ isOpen, toggle }) {
  return (
    <aside
      className={`
        bg-gray-800 
        w-64 
        flex flex-col 
        transition-transform duration-300 
        transform 
        ${isOpen ? "translate-x-0" : "-translate-x-full"} 
        md:translate-x-0 
        md:static 
        fixed 
        inset-y-0 
        left-0 
        z-20
      `}
    >
      {/* Close button for mobile */}
      <button
        onClick={toggle}
        className="self-end m-4 md:hidden p-2 rounded hover:bg-gray-700 focus:outline-none"
        aria-label="Close sidebar"
      >
        <svg
          className="w-5 h-5 text-gray-200"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>

      {/* Sidebar content */}
      <nav className="flex-1 px-4 py-6 overflow-y-auto">
        <h2 className="text-xl font-semibold mb-4">Channels</h2>
        <ul className="space-y-2">
          <li>
            <a
              href="#"
              className="block py-2 px-3 rounded hover:bg-gray-700 transition-colors"
            >
              General
            </a>
          </li>
          <li>
            <a
              href="#"
              className="block py-2 px-3 rounded hover:bg-gray-700 transition-colors"
            >
              Random
            </a>
          </li>
          {/* Add more items as needed */}
        </ul>
      </nav>
    </aside>
  );
}