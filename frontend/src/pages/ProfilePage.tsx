import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { fetchMyProfile, readProfileSaveError, updateMyName } from "@/lib/api/profile";
import { profileNameUpdate } from "@/lib/profileName";

const fieldClass =
  "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-600";

const ProfilePage = () => {
  const auth = useAuth();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [savedFirstName, setSavedFirstName] = useState("");
  const [savedLastName, setSavedLastName] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchMyProfile()
      .then((profile) => {
        if (cancelled) {
          return;
        }
        const first = profile.first_name || "";
        const last = profile.last_name || "";
        setEmail(profile.email || "");
        setPhone(profile.phone_number || "");
        setSavedFirstName(first);
        setSavedLastName(last);
        setFirstName(first);
        setLastName(last);
        setEditing(!first.trim() || !last.trim());
        auth.updateProfile({ firstName: first, lastName: last });
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError("Could not load your profile.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [auth.updateProfile]);

  const startEditing = () => {
    setFirstName(savedFirstName);
    setLastName(savedLastName);
    setError("");
    setSuccess("");
    setEditing(true);
  };

  const cancelEditing = () => {
    setFirstName(savedFirstName);
    setLastName(savedLastName);
    setError("");
    setEditing(false);
  };

  const saveName = async () => {
    const parsed = profileNameUpdate(firstName, lastName);
    if (parsed.ok === false) {
      setSuccess("");
      setError(parsed.message);
      return;
    }
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const profile = await updateMyName(parsed.first_name, parsed.last_name);
      const first = profile.first_name || parsed.first_name;
      const last = profile.last_name || parsed.last_name;
      setSavedFirstName(first);
      setSavedLastName(last);
      setFirstName(first);
      setLastName(last);
      auth.updateProfile({ firstName: first, lastName: last });
      setEditing(false);
      setSuccess("Profile saved.");
    } catch (saveError) {
      setError(readProfileSaveError(saveError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 p-4 md:p-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
        <h3 className="text-lg font-semibold text-black dark:text-white">Profile</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">Manage your profile information and settings</p>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-800">
          <h4 className="text-base font-semibold text-slate-900 dark:text-white mb-4">Personal Information</h4>
          {loading ? <p className="text-sm text-gray-600">Loading profile...</p> : null}
          {loadError ? <p className="text-sm text-red-600" role="alert">{loadError}</p> : null}
          {!loading && !loadError ? (
            <div className="space-y-4">
              <div>
                <label htmlFor="profile-first-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">First name</label>
                <input
                  id="profile-first-name"
                  type="text"
                  className={fieldClass}
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                  disabled={!editing || saving}
                  autoComplete="given-name"
                />
              </div>
              <div>
                <label htmlFor="profile-last-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Last name</label>
                <input
                  id="profile-last-name"
                  type="text"
                  className={fieldClass}
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                  disabled={!editing || saving}
                  autoComplete="family-name"
                />
              </div>
              <div>
                <label htmlFor="profile-email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
                <input id="profile-email" type="email" className={fieldClass} value={email} disabled readOnly />
              </div>
              <div>
                <label htmlFor="profile-phone" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Phone</label>
                <input id="profile-phone" type="tel" className={fieldClass} value={phone} disabled readOnly />
              </div>
              {error ? <p className="text-sm text-red-600" role="alert">{error}</p> : null}
              {success ? <p className="text-sm text-green-700" role="status">{success}</p> : null}
              {editing ? (
                <div className="flex gap-3">
                  <button
                    type="button"
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60"
                    onClick={saveName}
                    disabled={saving}
                  >
                    {saving ? "Saving..." : "Save"}
                  </button>
                  <button
                    type="button"
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-slate-700 hover:bg-gray-50 disabled:opacity-60"
                    onClick={cancelEditing}
                    disabled={saving}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  onClick={startEditing}
                >
                  Edit
                </button>
              )}
            </div>
          ) : null}
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
