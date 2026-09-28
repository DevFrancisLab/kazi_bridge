const recommendations = [
  { name: "John M.", skill: "UI/UX Designer", match: 95 },
  { name: "Leah K.", skill: "Frontend Developer", match: 92 },
  { name: "Peter S.", skill: "Product Manager", match: 88 },
];

const AIRecommendations = () => {
  return (
    <section className="rounded-2xl border border-gray-200 bg-gradient-to-br from-blue-50 via-white to-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white">KaziBridge AI Suggestions</h3>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-300">Auto-generated matches based on your recent job activity.</p>

      <div className="mt-4 space-y-3">
        {recommendations.map((item) => (
          <div
            key={item.name}
            className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-3 shadow-sm transition hover:shadow-md dark:border-gray-700 dark:bg-slate-900"
          >
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">{item.name}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{item.skill}</p>
            </div>
            <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">{item.match}% match</span>
          </div>
        ))}
      </div>
    </section>
  );
};

export default AIRecommendations;
