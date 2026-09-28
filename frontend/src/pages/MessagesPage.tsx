import { useState } from "react";

const messages = [
  { id: 1, from: "Samuel N.", subject: "Proposal update", snippet: "I've revised the plan based on your feedback..." },
  { id: 2, from: "Asha M.", subject: "Timeline confirmation", snippet: "I can start next week and deliver in 3 weeks..." },
  { id: 3, from: "David K.", subject: "Budget proposal", snippet: "I can do a discounted package if you commit..." },
];

type Message = (typeof messages)[number];

const MessagesPage = () => {
  const [selected, setSelected] = useState<Message | null>(null);
  const [reply, setReply] = useState("");

  const handleSend = () => {
    if (!selected || !reply.trim()) return;
    alert(`Sent to ${selected.from}: ${reply}`);
    setReply("");
  };

  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Messages</h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">Track conversations with freelancers.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          {messages.map((item) => (
            <button
              key={item.id}
              onClick={() => setSelected(item)}
              className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                selected?.id === item.id
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50 dark:border-gray-700 dark:bg-slate-800"
              }`}
            >
              <div className="flex items-center justify-between">
                <p className="font-semibold text-slate-900 dark:text-white">{item.from}</p>
                <span className="text-xs text-gray-500">Unread</span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-300">{item.subject}</p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{item.snippet}</p>
            </button>
          ))}
        </div>

        <div className="md:col-span-2">
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-slate-800">
            {selected ? (
              <>
                <p className="text-sm text-gray-500 dark:text-gray-300">To: {selected.from}</p>
                <p className="mb-4 text-xl font-semibold text-slate-900 dark:text-white">{selected.subject}</p>
                <p className="mb-4 text-sm text-gray-600 dark:text-gray-300">{selected.snippet}</p>
                <textarea
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  rows={4}
                  placeholder="Type your response..."
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 dark:border-gray-700 dark:bg-slate-900 dark:text-white"
                />
                <button
                  onClick={handleSend}
                  className="mt-3 rounded-lg px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
                  style={{ backgroundColor: '#70e000' }}
                >
                  Send
                </button>
              </>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">Select a message to reply.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default MessagesPage;
