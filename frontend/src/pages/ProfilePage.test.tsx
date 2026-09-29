import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "@/context/AuthContext";
import ProfilePage from "@/pages/ProfilePage";

const fetchMyProfile = vi.fn();
const updateMyName = vi.fn();

vi.mock("@/lib/api/profile", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/profile")>("@/lib/api/profile");
  return {
    ...actual,
    fetchMyProfile: (...args: unknown[]) => fetchMyProfile(...args),
    updateMyName: (...args: unknown[]) => updateMyName(...args),
  };
});

const profile = {
  id: 14,
  email: "freelancer@example.com",
  phone_number: "+254712345678",
  first_name: "",
  last_name: "",
  role: "FREELANCER",
  skills: "",
  is_active: true,
  created_at: "2026-09-29T00:00:00Z",
};

function renderProfile() {
  localStorage.setItem("token", "test-token");
  localStorage.setItem("role", "FREELANCER");
  localStorage.setItem("email", "freelancer@example.com");
  return render(
    <AuthProvider>
      <ProfilePage />
    </AuthProvider>,
  );
}

describe("ProfilePage", () => {
  beforeEach(() => {
    localStorage.clear();
    fetchMyProfile.mockReset();
    updateMyName.mockReset();
    fetchMyProfile.mockResolvedValue(profile);
  });

  it("loads the signed-in profile and does not show a placeholder name", async () => {
    renderProfile();
    expect(await screen.findByLabelText("First name")).toHaveValue("");
    expect(screen.getByLabelText("Last name")).toHaveValue("");
    expect(screen.getByLabelText("Email")).toHaveValue("freelancer@example.com");
    expect(screen.getByLabelText("Phone")).toHaveValue("+254712345678");
    expect(screen.queryByDisplayValue("John Doe")).not.toBeInTheDocument();
    expect(updateMyName).not.toHaveBeenCalled();
  });

  it("blocks an empty save and sends only a trimmed name", async () => {
    updateMyName.mockResolvedValue({ ...profile, first_name: "Nia", last_name: "Kamau" });
    renderProfile();
    await screen.findByLabelText("First name");

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Enter your first and last name.");
    expect(updateMyName).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("First name"), { target: { value: "  Nia  " } });
    fireEvent.change(screen.getByLabelText("Last name"), { target: { value: "  Kamau  " } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(updateMyName).toHaveBeenCalledWith("Nia", "Kamau");
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Profile saved.");
    expect(localStorage.getItem("first_name")).toBe("Nia");
    expect(localStorage.getItem("last_name")).toBe("Kamau");
  });
});
