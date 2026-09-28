import { DashboardContent } from "@/components/DashboardLayout";

const ProfilePage = () => {
  return (
    <div className="space-y-6 p-4 md:p-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h3 className="text-lg font-semibold text-black dark:text-white">Profile</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">Manage your profile information and settings</p>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
          <h4 className="text-base font-semibold text-slate-900 dark:text-white mb-4">Personal Information</h4>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Full Name</label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                defaultValue="John Doe"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
              <input
                type="email"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                defaultValue="john.doe@example.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Phone</label>
              <input
                type="tel"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                defaultValue="+254 712 345 678"
              />
            </div>

            <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Update Profile
            </button>
          </div>
        </section>

        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
          <h4 className="text-base font-semibold text-slate-900 dark:text-white mb-4">Skills & Expertise</h4>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Primary Skills</label>
              <div className="flex flex-wrap gap-2">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">React</span>
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">TypeScript</span>
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">Node.js</span>
                <span className="px-3 py-1 bg-green-100 text-green-800 text-sm rounded-full">+ Add Skill</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Experience Level</label>
              <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                <option>Junior (1-3 years)</option>
                <option>Mid-level (3-5 years)</option>
                <option>Senior (5+ years)</option>
                <option>Expert (8+ years)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Hourly Rate</label>
              <input
                type="number"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="KES per hour"
                defaultValue="2500"
              />
            </div>

            <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Update Skills
            </button>
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h4 className="text-base font-semibold text-slate-900 dark:text-white mb-4">Portfolio</h4>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-lg border-2 border-dashed border-gray-300 p-4 text-center">
            <div className="text-gray-400 mb-2">
              <svg className="mx-auto h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Add project screenshot</p>
            <button className="mt-2 text-blue-600 text-sm hover:text-blue-700">Upload</button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default ProfilePage;